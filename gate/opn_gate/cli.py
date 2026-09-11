"""The gate's command line: one codebase, three invocations (D-4; F00-R11).

    python -m opn_gate.cli pregate --graph <graph-checkout> --node <id> [--sign KEY] ...

``gate/pregate.sh`` wraps ``pregate``. Exit codes: 0 pass · 1 fail · 3 bounced · 2 usage or
internal error before a verdict existed. Every run that reaches the pipeline writes
``verdict.json`` and ``attestation.json`` and prints the verdict summary as JSON on stdout, so an
agent can parse it and self-correct (D-27).
"""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
import tempfile
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from opn_gate import (
    admit,
    attestation,
    bounce,
    cache,
    config,
    curator,
    exhibits,
    layout,
    ledger,
    modes,
    objectstore,
    paths,
    pipeline,
    postmerge,
    products,
    sandbox,
    scaffold,
    schemas,
    signer,
    toolchain,
)
from opn_gate import graph as graphmod
from opn_gate.paths import Change, Claim
from opn_gate.steps.base import RunContext
from opn_gate.steps.hazards import HazardsStep, StatementStep
from opn_gate.steps.toolchain_step import ToolchainStep

GATE_DIR = Path(__file__).resolve().parents[1]

log = logging.getLogger("opn_gate")

EXIT_PASS = 0
EXIT_FAIL = 1
EXIT_ERROR = 2
EXIT_BOUNCED = 3


class CliError(Exception):
    """A problem with the invocation itself, reported before any verdict exists."""


#: The curator's commands (F08-R9 to R12): what one of them refuses is answered as
#: ``{"ok": false, "refused": ...}`` and exit 1, whichever module raised it.
CURATOR_COMMANDS: frozenset[str] = frozenset({"revise", "consolidate", "status", "missing-library"})
#: What a curator command refuses on: a record that does not satisfy its schema, a statement the
#: scaffold cannot take, a graph that does not derive. Anywhere else these are exit 2.
_REFUSALS: tuple[type[Exception], ...] = (
    schemas.SchemaError,
    scaffold.ScaffoldError,
    graphmod.GraphError,
)
#: The gate's own error family, plus the OS's for a flag file that cannot be read: an input or
#: environment problem, reported on stderr as exit 2 — never a traceback (conventions §5; F08-Q18).
_ENVIRONMENT_ERRORS: tuple[type[Exception], ...] = (
    *_REFUSALS,
    signer.SignerError,
    sandbox.SandboxError,
    toolchain.ToolchainError,
    toolchain.ToolchainMissingError,
    postmerge.GraphWriteError,
    OSError,
)
DATE_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def positive_int(text: str) -> int:
    """An argparse type for a count with a lower bound of one (F08-R11: K below 1 makes D-33's
    attempt threshold vacuous)."""
    try:
        value = int(text)
    except ValueError:
        msg = f"{text!r} is not an integer"
        raise argparse.ArgumentTypeError(msg) from None
    if value < 1:
        msg = f"must be at least 1, got {value}"
        raise argparse.ArgumentTypeError(msg)
    return value


def build_parser() -> argparse.ArgumentParser:  # noqa: PLR0915 — one statement per flag
    parser = argparse.ArgumentParser(prog="opn-gate", description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)

    pre = sub.add_parser("pregate", help="run gate steps 1, 2 and 4-8 locally on one node")
    pre.add_argument("--graph", required=True, type=Path, help="path to the graph checkout")
    pre.add_argument("--node", required=True, help="the claimed node id")
    pre.add_argument("--target", help="target id (inferred when the graph has exactly one)")
    pre.add_argument("--base", default=None, help="git ref to diff against (default: HEAD)")
    pre.add_argument("--sign", type=Path, metavar="KEY", help="sign with this SSH private key")
    pre.add_argument("--model", help="model used, as declared (D-23)")
    pre.add_argument("--harness", help="harness used, as declared (D-23)")
    pre.add_argument("--out", type=Path, help="output directory (default: a fresh temp dir)")
    pre.add_argument("--install", action="store_true", help="let elan install the pinned toolchain")
    pre.add_argument("--no-diff", action="store_true", help="skip the diff (bare tree, no git)")

    rep = sub.add_parser("reproduce", help="replay a merged commit inside the step-3 image (D-5)")
    rep.add_argument("--graph", required=True, type=Path, help="path to the graph checkout")
    rep.add_argument("--commit", required=True, help="the commit to reproduce")
    rep.add_argument("--node", required=True, help="the node the commit proved")
    rep.add_argument("--target", help="target id (inferred when the graph has exactly one)")
    rep.add_argument("--compare", type=Path, help="committed attestation to compare against")
    _add_sandbox_args(rep)

    gate = sub.add_parser("gate", help="the authoritative run on a pull request (gate.yml)")
    gate.add_argument("--graph", required=True, type=Path, help="checkout at the PR merge commit")
    gate.add_argument("--base", required=True, help="the pull request's base sha")
    gate.add_argument("--head", default="HEAD", help="the commit to check (default HEAD)")
    gate.add_argument("--target", required=True)
    gate.add_argument("--node", required=True)
    gate.add_argument("--pr-body-file", required=True, type=Path)
    _add_sandbox_args(gate)

    post = sub.add_parser("postmerge", help="re-derive on the merge commit; record step 9")
    post.add_argument("--graph", required=True, type=Path)
    post.add_argument("--commit", required=True, help="the merge commit")
    post.add_argument("--pr", required=True, type=int, help="the merged pull request number")
    post.add_argument(
        "--review-kind",
        required=True,
        choices=["tutorial", "pr-approval", "certificate", "provenance"],
        help="what satisfies step 9 for this node (D-4 v3.11)",
    )
    post.add_argument("--reviewer", help="the approving non-author reviewer (pr-approval)")
    post.add_argument("--review-reference", help="certificate id or registry reference")
    post.add_argument(
        "--approval-body-file",
        type=Path,
        action="append",
        default=[],
        help="an approving review's body; a waived proof needs one naming the waiver (F02-R9)",
    )
    post.add_argument("--target", required=True)
    post.add_argument("--node", required=True)
    _add_sandbox_args(post)

    cls = sub.add_parser("classify", help="what kind of pull request this is (F07-R3)")
    cls.add_argument("--graph", required=True, type=Path, help="checkout at the PR merge commit")
    cls.add_argument("--base", required=True, help="the pull request's base sha")
    cls.add_argument("--head", default="HEAD", help="the commit to classify (default HEAD)")
    cls.add_argument(
        "--author",
        help="the login that opened the pull request; curator mode needs it listed in "
        "curators.json (F08-R8). Default: OPN_PR_AUTHOR from the environment",
    )

    _add_graph_tool_parsers(sub)
    _add_curator_parsers(sub)
    _add_cache_parsers(sub)

    sign = sub.add_parser("sign", help="sign an attestation with the gate key from the environment")
    sign.add_argument("--attestation", required=True, type=Path)
    sign.add_argument("--public-key", required=True, type=Path, help="keys/gate.pub to verify")
    sign.add_argument("--out", required=True, type=Path)
    return parser


def _add_graph_tool_parsers(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """The graph-side tools that are not proof runs: admission (F08), exhibits (F08), step 6
    alone (F02) and the products (F03)."""
    exh = sub.add_parser("exhibits", help="elaborate the Lean exhibits an append carries (F08)")
    exh.add_argument("--graph", required=True, type=Path, help="checkout at the PR merge commit")
    exh.add_argument("--base", required=True, help="the pull request's base sha")
    exh.add_argument("--head", default="HEAD", help="the commit to check (default HEAD)")
    exh.add_argument("--out", type=Path, help="work directory (default: a fresh temp dir)")
    exh.add_argument("--install", action="store_true", help="let elan install the pinned toolchain")
    exh.add_argument("--sandbox", action="store_true", help="elaborate inside the step-3 image")
    exh.add_argument("--image", help="sandbox image tag (default: built from gate/Dockerfile)")
    exh.add_argument("--no-build", action="store_true", help="fail if the image is not present")

    adm = sub.add_parser("admit", help="may this node directory enter the graph? (F08-R1)")
    adm.add_argument("node_dir", type=Path, help="targets/<target>/nodes/<id> in a graph checkout")
    adm.add_argument("--out", type=Path, help="work directory (default: a fresh temp dir)")
    adm.add_argument("--install", action="store_true", help="let elan install the pinned toolchain")
    adm.add_argument(
        "--sandbox",
        action="store_true",
        help="elaborate inside the step-3 image, as the authoritative gate must (F08-R2, C9)",
    )
    adm.add_argument("--image", help="sandbox image tag (default: built from gate/Dockerfile)")
    adm.add_argument("--no-build", action="store_true", help="fail if the image is not present")

    haz = sub.add_parser("hazards", help="run step 6 alone on a node directory (F02-R7)")
    haz.add_argument("node_dir", type=Path, help="targets/<target>/nodes/<id> in a graph checkout")
    haz.add_argument("--out", type=Path, help="work directory (default: a fresh temp dir)")
    haz.add_argument("--install", action="store_true", help="let elan install the pinned toolchain")

    prod = sub.add_parser("products", help="regenerate the merge products (F03; D-35)")
    prod.add_argument("--graph", required=True, type=Path, help="path to the graph checkout")
    prod.add_argument("--commit", default="HEAD", help="the commit the products render (git)")
    prod.add_argument("--out", type=Path, help="write here instead of into the checkout")
    prod.add_argument("--no-meta", action="store_true", help="do not rewrite META.yaml status")
    prod.add_argument(
        "--claims-url",
        help="the service's GET /claims.json; refreshes claims.json, keeping the committed "
        "snapshot if the service is unreachable (F05-R10)",
    )


def _add_curator_parsers(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """The curator's commands (F08-R9 to R12) and the post-merge ledger writer (F08-R13)."""

    def common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--graph", required=True, type=Path, help="path to the graph checkout")
        p.add_argument("--target", help="target id (inferred when the graph has exactly one)")
        p.add_argument("--author", required=True, help="the curator's pseudonym, on the record")
        p.add_argument("--date", help="UTC timestamp of the act (default: now)")
        p.add_argument(
            "--branch",
            help="also create this git branch and commit what was written, ready for a curator "
            "pull request (F08-R8)",
        )

    rev = sub.add_parser("revise", help="version a defective statement (F08-R9; D-8)")
    common(rev)
    rev.add_argument("node_id", help="the node whose statement is defective")
    rev.add_argument("--statement", required=True, type=Path, help="the new Statement.lean")
    rev.add_argument("--request", required=True, type=Path, help="the revision request acted on")

    con = sub.add_parser("consolidate", help="mark a duplicate node superseded (F08-R10; D-29)")
    common(con)
    con.add_argument("keep", help="the node that stays")
    con.add_argument("drop", help="the node that is superseded by it")
    con.add_argument("--no-toolchain", action="store_true", help="accept identical hashes only")
    con.add_argument("--out", type=Path, help="work directory (default: a fresh temp dir)")
    con.add_argument("--install", action="store_true", help="let elan install the pinned toolchain")
    con.add_argument("--sandbox", action="store_true", help="elaborate inside the step-3 image")
    con.add_argument("--image", help="sandbox image tag (default: built from gate/Dockerfile)")
    con.add_argument("--no-build", action="store_true", help="fail if the image is not present")

    st = sub.add_parser("status", help="an abandonment or dormancy record (F08-R11; D-14, D-33)")
    common(st)
    st.add_argument("ref", help="a node id (abandoned) or the target id (dormant, active)")
    st.add_argument("status", choices=[*curator.NODE_STATUSES, *curator.TARGET_STATUSES])
    st.add_argument("--cause", required=True, help="the published reasoning (D-33 b)")
    st.add_argument(
        "--k", type=positive_int, default=curator.DEFAULT_K, help="D-33's K in force (at least 1)"
    )
    st.add_argument("--n", type=int, default=curator.DEFAULT_N_DAYS, help="D-33's N (days)")

    ml = sub.add_parser("missing-library", help="the D-13 aggregate for the curator (F08-R12)")
    ml.add_argument("--graph", required=True, type=Path, help="path to the graph checkout")
    ml.add_argument("--target", help="target id (inferred when the graph has exactly one)")
    ml.add_argument("--threshold", type=int, default=curator.DEFAULT_THRESHOLD)

    led = sub.add_parser("ledger", help="the statement line for a merged proposal (F08-R13)")
    led.add_argument("--graph", required=True, type=Path)
    led.add_argument("--commit", required=True, help="the merge commit")


def _add_cache_parsers(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """The olean cache (F10-R7, R8): ``cache fetch`` for a checkout, ``cache publish`` for the
    post-merge job."""
    top = sub.add_parser("cache", help="the olean cache a graph names in gate-spec.json (F10)")
    ops = top.add_subparsers(dest="cache_command", required=True)
    fetch = ops.add_parser("fetch", help="fetch the newest verified cache at or before a commit")
    fetch.add_argument("--graph", required=True, type=Path, help="path to the graph checkout")
    fetch.add_argument("--target", help="target id (inferred when the graph has exactly one)")
    fetch.add_argument("--commit", default="HEAD", help="the graph commit to key on")
    fetch.add_argument("--out", type=Path, help="where to put it (default: a fresh temp dir)")
    pub = ops.add_parser("publish", help="build the merged tree's oleans, pack, upload (postmerge)")
    pub.add_argument("--graph", required=True, type=Path, help="path to the graph checkout")
    pub.add_argument("--commit", default="HEAD", help="the merge commit the cache is keyed by")
    pub.add_argument("--target", help="target id (inferred when the graph has exactly one)")
    pub.add_argument("--bucket", help="the S3 bucket to upload to (omit: build and pack only)")
    pub.add_argument("--prefix", default="", help="key prefix inside the bucket")
    pub.add_argument("--out", type=Path, help="work directory (default: a fresh temp dir)")
    pub.add_argument("--install", action="store_true", help="let elan install the pinned toolchain")
    pub.add_argument("--sandbox", action="store_true", help="build inside the step-3 image")
    pub.add_argument("--image", help="sandbox image tag (default: from the spec, or built)")
    pub.add_argument("--no-build", action="store_true", help="fail if the image is not present")


def _add_sandbox_args(p: argparse.ArgumentParser) -> None:
    """The flags every sandboxed run shares (reproduce, gate, postmerge)."""
    p.add_argument("--out", type=Path, help="output directory (default: a fresh temp dir)")
    p.add_argument("--image", help="sandbox image tag (default: built from gate/Dockerfile)")
    p.add_argument("--no-build", action="store_true", help="fail if the image is not present")


def main(argv: Sequence[str] | None = None) -> int:
    """Every command, behind the one boundary where the gate's errors become exit codes: a
    ``CliError`` or any input/environment error is exit 2 on stderr; a curator command's refusal
    is ``{"ok": false, "refused": ...}`` and exit 1 (conventions §5)."""
    args = build_parser().parse_args(argv)
    try:
        settings = config.load()
    except config.ConfigError as exc:
        return _usage_error(exc)
    logging.basicConfig(level=settings.log_level, format="%(levelname)s %(name)s: %(message)s")
    commands = {
        "pregate": run_pregate,
        "reproduce": run_reproduce,
        "gate": run_gate,
        "classify": run_classify,
        "exhibits": run_exhibits,
        "revise": run_revise,
        "consolidate": run_consolidate,
        "status": run_status,
        "missing-library": run_missing_library,
        "ledger": run_ledger,
        "postmerge": run_postmerge,
        "admit": run_admit,
        "hazards": run_hazards,
        "products": run_products,
        "sign": run_sign,
        "cache": run_cache,
    }
    try:
        return commands[args.command](args, settings)
    except CliError as exc:
        return _usage_error(exc)
    except curator.CuratorError as exc:  # a refusal, with the reason: nothing was written
        return _refused(exc)
    except _REFUSALS as exc:
        return _refused(exc) if args.command in CURATOR_COMMANDS else _usage_error(exc)
    except _ENVIRONMENT_ERRORS as exc:
        return _usage_error(exc)


def _usage_error(exc: Exception) -> int:
    sys.stderr.write(f"opn-gate: {exc}\n")
    return EXIT_ERROR


def _refused(exc: Exception) -> int:
    sys.stdout.write(json.dumps({"ok": False, "refused": str(exc)}, indent=2) + "\n")
    sys.stderr.write(f"opn-gate: refused: {exc}\n")
    return EXIT_FAIL


def _read_flag_file(path: Path, flag: str) -> str:
    """The text a flag names — read before any expensive work, so a wrong path is a usage
    error and not a traceback after the export, the image build and the run (F08-Q18)."""
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        msg = f"cannot read {flag} {path}: {exc.strerror or exc}"
        raise CliError(msg) from exc


# --- pregate ------------------------------------------------------------------------------------


def run_pregate(args: argparse.Namespace, settings: config.Settings) -> int:
    graph: Path = args.graph.resolve()
    if not graph.is_dir():
        msg = f"graph checkout not found: {graph}"
        raise CliError(msg)
    target_id = args.target or infer_target(graph)
    claim = Claim(target_id, args.node)
    spec_path = layout.gate_spec_path(graph, target_id)
    try:
        spec = schemas.load_json(spec_path, "gate-spec/v1")
    except schemas.SchemaError as exc:
        msg = f"cannot load {spec_path}: {exc}"
        raise CliError(msg) from exc
    try:
        tc = toolchain.LocalToolchain.from_settings(settings)
    except toolchain.ToolchainMissingError as exc:
        raise CliError(str(exc)) from exc
    if args.sign is not None and not args.sign.is_file():
        msg = f"--sign {args.sign} is not a file"
        raise CliError(msg)

    changes: list[Change] | None = None if args.no_diff else worktree_changes(graph, args.base)
    out_dir: Path = (args.out or Path(tempfile.mkdtemp(prefix="opn-pregate-"))).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    ctx = RunContext(
        graph_root=graph,
        claim=claim,
        spec=spec,
        gate_spec_hash=schemas.content_hash(spec_path.read_bytes()),
        changes=changes,
        workdir=out_dir / "work",
        toolchain=tc,
        settings=settings,
        install_toolchain=bool(args.install),
    )
    fetched = attach_cache(ctx, graph, head_commit(graph), out_dir)
    verdict = pipeline.run_submission(ctx)
    doc = attestation.build(
        ctx,
        verdict,
        graph_commit=None if args.no_diff else clean_head(graph),
        tooling={"model": args.model, "harness": args.harness},
    )
    if args.sign is not None:
        try:
            sig = signer.SshKeygenSigner().sign(
                attestation.signed_bytes(doc), args.sign, "contributor"
            )
        except signer.SignerError as exc:
            msg = f"cannot sign with {args.sign}: {exc}"
            raise CliError(msg) from exc
        doc["signature"] = {
            "kind": sig.kind,
            "key_id": sig.key_id,
            "value": sig.value,
            "timestamp": doc["signature"]["timestamp"],
        }
        schemas.validate(doc, attestation.SCHEMA)
    return emit(verdict, doc, out_dir, settings, olean_cache=cache_report(ctx, fetched))


def head_commit(graph: Path) -> str | None:
    """HEAD's sha whether or not the tree is dirty (the cache is keyed by ancestry, F10-R7);
    ``None`` for a bare tree."""
    if _git(graph, "rev-parse", "--is-inside-work-tree").returncode != 0:
        return None
    head = _git(graph, "rev-parse", "HEAD")
    return head.stdout.strip() if head.returncode == 0 and head.stdout.strip() else None


def attach_cache(
    ctx: RunContext, git_root: Path, commit: str | None, out_dir: Path
) -> cache.FetchResult:
    """F10-R7: fetch the newest olean cache at or before ``commit`` into the run's directory and
    hand it to the build step; a miss, a corrupt archive or an unreachable store means the run
    builds everything itself (C7) and says so in the summary."""
    result = cache.prepare(ctx.spec, git_root, commit, out_dir / "olean-cache")
    ctx.data["olean_cache_usage"] = cache.Usage(commit=result.commit)
    if result.fetched is not None:
        ctx.data["olean_cache"] = result.fetched
    return result


def cache_report(ctx: RunContext, fetched: cache.FetchResult) -> dict[str, Any]:
    usage: cache.Usage | None = ctx.data.get("olean_cache_usage")
    report = fetched.as_dict()
    report.update(usage.as_dict() if usage is not None else {"hits": [], "misses": []})
    return report


def emit(
    verdict: pipeline.Verdict,
    doc: dict[str, Any],
    out_dir: Path,
    settings: config.Settings,
    *,
    olean_cache: dict[str, Any] | None = None,
) -> int:
    """Write the verdict and the attestation, print the summary. The cache report rides in the
    summary and ``cache.json`` only: the attestation is a function of the tree and the pinned
    tooling alone (D-5), and whether a dependency's olean was compiled or fetched is not."""
    verdict_doc = verdict.as_dict(settings.diagnostic_max_bytes)
    (out_dir / "verdict.json").write_bytes(schemas.canonical_json(verdict_doc))
    (out_dir / "attestation.json").write_bytes(schemas.canonical_json(doc))
    summary = dict(verdict_doc)
    summary["attestation"] = str(out_dir / "attestation.json")
    summary["verdict_file"] = str(out_dir / "verdict.json")
    if olean_cache is not None:
        (out_dir / "cache.json").write_bytes(schemas.canonical_json(olean_cache))
        summary["olean_cache"] = olean_cache
    sys.stdout.write(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    if verdict.verdict == "pass":
        return EXIT_PASS
    if verdict.verdict == "bounced":
        return EXIT_BOUNCED
    return EXIT_FAIL


# --- reproduce ----------------------------------------------------------------------------------


def run_reproduce(args: argparse.Namespace, settings: config.Settings) -> int:
    graph, commit = _checkout_and_commit(args.graph, args.commit)
    committed: dict[str, Any] | None = None
    if args.compare is not None:  # read before the run, so a wrong path costs no sandbox
        try:
            committed = schemas.load_json(args.compare)
        except schemas.SchemaError as exc:
            msg = f"cannot load --compare {args.compare}: {exc}"
            raise CliError(msg) from exc
    out_dir = _out_dir(args.out, "opn-reproduce-")
    ctx = _sandboxed_context(
        graph,
        commit,
        out_dir,
        target=args.target,
        node=args.node,
        settings=settings,
        image=args.image,
        no_build=args.no_build,
    )
    verdict = pipeline.run_submission(ctx)
    doc = attestation.build(ctx, verdict, graph_commit=commit)
    code = emit(verdict, doc, out_dir, settings)
    if committed is not None:
        differing = attestation.compare(committed, attestation.with_step9(doc, committed))
        result = {"identical": not differing, "differing_fields": differing}
        sys.stdout.write(json.dumps(result) + "\n")
        return EXIT_PASS if not differing else EXIT_FAIL
    return code


def run_gate(args: argparse.Namespace, settings: config.Settings) -> int:
    """The authoritative run: bounce rule, then steps 1, 2 and 4-8 in the sandbox (hosted)."""
    graph, head = _checkout_and_commit(args.graph, args.head)
    base = _git(graph, "rev-parse", "--verify", f"{args.base}^{{commit}}").stdout.strip()
    if not base:
        msg = f"unknown base {args.base!r}"
        raise CliError(msg)
    pr_body = _read_flag_file(args.pr_body_file, "--pr-body-file")
    out_dir = _out_dir(args.out, "opn-gate-")
    ctx = _sandboxed_context(
        graph,
        head,
        out_dir,
        target=args.target,
        node=args.node,
        settings=settings,
        image=args.image,
        no_build=args.no_build,
    )
    diff = _git(graph, "diff", "--name-status", "--no-renames", base, head)
    ctx.changes = paths.changes_from_name_status(diff.stdout)
    node_dir = layout.graph_nodes_dir(ctx.graph_root, args.target) / args.node
    statement = node_dir / "Statement.lean"
    policy = bounce.PrecheckPolicy(
        pr_body=pr_body,
        accepted_signatures=tuple(ctx.spec["accepted_precheck_signatures"]),
        max_age_s=int(ctx.spec["precheck_max_age_s"]),
        now=attestation.utc_now(),
        node_id=args.node,
        statement_hash=schemas.content_hash(statement.read_bytes()) if statement.is_file() else "",
    )
    fetched = attach_cache(ctx, graph, head, out_dir)
    verdict = pipeline.run_submission(ctx, precheck=policy)
    doc = attestation.build(ctx, verdict, graph_commit=head)
    return emit(verdict, doc, out_dir, settings, olean_cache=cache_report(ctx, fetched))


def run_classify(args: argparse.Namespace, settings: config.Settings) -> int:
    """F07-R3: what kind of pull request this is, and — for the kinds that build nothing — the
    whole of their checking (R9, R10).

    The workflow runs this before it decides whether to spend a sandbox on the diff: an append or
    an explainer is finished here, a proof or a partial goes on to ``gate``. Exit 0 means the
    classification stands and every check that applies to it passed; 1 means it is refused, with
    every reason in ``problems``.
    """
    graph, head = _checkout_and_commit(args.graph, args.head)
    base = _git(graph, "rev-parse", "--verify", f"{args.base}^{{commit}}").stdout.strip()
    if not base:
        msg = f"unknown base {args.base!r}"
        raise CliError(msg)
    diff = _git(graph, "diff", "--name-status", "--no-renames", base, head)
    try:
        curators = modes.load_curators(graph)
    except modes.CuratorsError as exc:
        raise CliError(str(exc)) from exc
    classification = modes.classify(
        paths.changes_from_name_status(diff.stdout),
        author=args.author or settings.pr_author,
        curators=curators,
    )
    problems = list(classification.problems)
    if classification.ok:
        problems.extend(modes.check(graph, classification, base=base_reader(graph, base)))
    summary = classification.as_dict()
    summary["problems"] = [d.as_dict(settings.diagnostic_max_bytes) for d in problems]
    summary["ok"] = classification.ok and not problems
    # F08-R6, R7: an append that carries a Lean exhibit still needs the sandbox, for that alone.
    carrying = modes.exhibits(graph, classification) if classification.ok else []
    summary["exhibits"] = [loc.path for loc in carrying]
    summary["needs_exhibits"] = bool(carrying)
    sys.stdout.write(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    if not summary["ok"]:
        for d in problems:
            sys.stderr.write(f"opn-gate: {d.code}: {d.message}\n")
    return EXIT_PASS if summary["ok"] else EXIT_FAIL


def run_exhibits(args: argparse.Namespace, settings: config.Settings) -> int:
    """F08-R6, R7: elaborate every exhibit the pull request's appended records carry.

    Contributor Lean, so ``--sandbox`` on the authoritative gate (C9). Exit 0 when every exhibit
    elaborates, 1 when one does not, naming it; a diff that is not an append is a usage error,
    because this command is the append mode's build and nothing else's.
    """
    graph, head = _checkout_and_commit(args.graph, args.head)
    base = _git(graph, "rev-parse", "--verify", f"{args.base}^{{commit}}").stdout.strip()
    if not base:
        msg = f"unknown base {args.base!r}"
        raise CliError(msg)
    diff = _git(graph, "diff", "--name-status", "--no-renames", base, head)
    classification = modes.classify(paths.changes_from_name_status(diff.stdout))
    if classification.mode != "append" or classification.target_id is None:
        msg = f"exhibits belong to append mode; this diff is {classification.mode!r}"
        raise CliError(msg)
    records = modes.exhibits(graph, classification)
    out_dir = _out_dir(args.out, "opn-exhibits-")
    workdir = out_dir / "work"
    spec_path = layout.gate_spec_path(graph, classification.target_id)
    try:
        spec = schemas.load_json(spec_path, "gate-spec/v1")
    except schemas.SchemaError as exc:
        msg = f"cannot load {spec_path}: {exc}"
        raise CliError(msg) from exc
    tc: toolchain.Toolchain
    if args.sandbox:
        tag = args.image or ensure_image(spec, build=not args.no_build)
        tc = sandbox.SandboxToolchain(tag, sandbox.Caps.from_spec(spec), read_write=[workdir])
    else:
        try:
            tc = toolchain.LocalToolchain.from_settings(settings)
        except toolchain.ToolchainMissingError as exc:
            raise CliError(str(exc)) from exc
    ctx = RunContext(
        graph_root=graph,
        claim=Claim(classification.target_id, classification.node_id or ""),
        spec=spec,
        gate_spec_hash=schemas.content_hash(spec_path.read_bytes()),
        changes=None,
        workdir=workdir,
        toolchain=tc,
        settings=settings,
        install_toolchain=bool(args.install) and not args.sandbox,
    )
    problems = exhibits.run(ctx, records)
    summary = {
        "ok": not problems,
        "exhibits": [loc.path for loc in records],
        "sandboxed": bool(args.sandbox),
        "problems": [d.as_dict(settings.diagnostic_max_bytes) for d in problems],
    }
    (out_dir / "exhibits.json").write_bytes(schemas.canonical_json(summary))
    sys.stdout.write(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    for d in problems:
        sys.stderr.write(f"opn-gate: {d.code}: {d.message}\n")
    return EXIT_PASS if not problems else EXIT_FAIL


def run_postmerge(args: argparse.Namespace, settings: config.Settings) -> int:
    """Re-derive on the merge commit and record step 9; signing is the separate `sign` step."""
    graph, commit = _checkout_and_commit(args.graph, args.commit)
    # The flags are checked before the sandbox is spent on the run (F08-Q18).
    try:
        review = postmerge.review_block(
            args.review_kind, reviewer=args.reviewer, reference=args.review_reference
        )
    except ValueError as exc:
        raise CliError(str(exc)) from exc
    bodies = [_read_flag_file(p, "--approval-body-file") for p in args.approval_body_file]
    out_dir = _out_dir(args.out, "opn-postmerge-")
    ctx = _sandboxed_context(
        graph,
        commit,
        out_dir,
        target=args.target,
        node=args.node,
        settings=settings,
        image=args.image,
        no_build=args.no_build,
    )
    verdict = pipeline.run_submission(ctx)
    doc = attestation.build(ctx, verdict, graph_commit=commit)
    doc = postmerge.record_step9(doc, merge_commit=commit, review=review)
    refusal = postmerge.check_waiver(doc, bodies)
    if refusal is not None:  # F02-R9: refuse to attest; nothing is written
        sys.stdout.write(json.dumps({"verdict": "refused", "diagnostic": refusal.as_dict()}) + "\n")
        sys.stderr.write(f"opn-gate: {refusal.message}\n")
        return EXIT_FAIL
    code = emit(verdict, doc, out_dir, settings)
    if code != EXIT_PASS:
        sys.stderr.write("opn-gate: the merged commit does not pass the gate; not attesting\n")
    return code


def run_admit(args: argparse.Namespace, settings: config.Settings) -> int:
    """F08-R1: the mechanical admission check over one node directory.

    Prints the verdict JSON — every check, in order, with the first failure named — and exits 0
    when the node may enter the graph, 1 when it may not. No attestation: admission decides
    whether a *statement* is well formed, which is not a claim about mathematics (D-29).
    """
    ctx = node_context(args, settings, prefix="opn-admit-", sandboxed=bool(args.sandbox))
    result = admit.run(ctx)
    summary = result.as_dict(settings.diagnostic_max_bytes)
    summary["node"] = ctx.claim.node_id
    summary["target"] = ctx.claim.target_id
    summary["sandboxed"] = bool(args.sandbox)
    for key in ("hazards", "relation", "relation_label", "statement_axioms", "witness"):
        if key in ctx.data:
            summary[key] = ctx.data[key]
    (ctx.workdir.parent / "admission.json").write_bytes(schemas.canonical_json(summary))
    sys.stdout.write(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    if not result.admitted and result.diagnostic is not None:
        sys.stderr.write(
            f"opn-gate: admission failed at {result.first_failing_check}: "
            f"{result.diagnostic.message}\n"
        )
    return EXIT_PASS if result.admitted else EXIT_FAIL


def node_context(
    args: argparse.Namespace, settings: config.Settings, *, prefix: str, sandboxed: bool = False
) -> RunContext:
    """A RunContext over one node directory in a graph checkout — no diff, no Proof.lean.

    ``sandboxed`` puts the toolchain inside the step-3 image with the same mounts the
    authoritative gate uses (F00-R5): the node read-only, the work directory read-write.
    """
    node_dir: Path = args.node_dir.resolve()
    parts = node_dir.parts
    if not node_dir.is_dir() or len(parts) < 4 or parts[-2] != "nodes" or parts[-4] != "targets":
        msg = f"{node_dir} is not a node directory (targets/<target>/nodes/<id>)"
        raise CliError(msg)
    graph = node_dir.parents[3]
    target_id = node_dir.parents[1].name
    spec_path = layout.gate_spec_path(graph, target_id)
    try:
        spec = schemas.load_json(spec_path, "gate-spec/v1")
    except schemas.SchemaError as exc:
        msg = f"cannot load {spec_path}: {exc}"
        raise CliError(msg) from exc
    out_dir = _out_dir(args.out, prefix)
    workdir = out_dir / "work"
    tc: toolchain.Toolchain
    if sandboxed:
        tag = getattr(args, "image", None) or ensure_image(
            spec, build=not getattr(args, "no_build", False)
        )
        tc = sandbox.SandboxToolchain(
            tag, sandbox.Caps.from_spec(spec), read_only=[node_dir], read_write=[workdir]
        )
    else:
        try:
            tc = toolchain.LocalToolchain.from_settings(settings)
        except toolchain.ToolchainMissingError as exc:
            raise CliError(str(exc)) from exc
    return RunContext(
        graph_root=graph,
        claim=Claim(target_id, node_dir.name),
        spec=spec,
        gate_spec_hash=schemas.content_hash(spec_path.read_bytes()),
        changes=None,
        workdir=workdir,
        toolchain=tc,
        settings=settings,
        install_toolchain=bool(args.install) and not sandboxed,
    )


def base_reader(graph: Path, base: str) -> modes.BaseReader:
    """What a path held at ``base`` (``git show``), or ``None`` when it did not exist there."""

    def read(path: str) -> bytes | None:
        proc = subprocess.run(
            ["git", "-C", str(graph), "show", f"{base}:{path}"],
            capture_output=True,
            check=False,
            env=git_environment(),
        )
        return proc.stdout if proc.returncode == 0 else None

    return read


def run_hazards(args: argparse.Namespace, settings: config.Settings) -> int:
    """F02-R7: step 6 alone over a node directory, for admission (F08) and proposers.

    Prints the verdict JSON plus a ``hazards`` block (findings, acknowledgments used); exits 0
    on pass, 1 on fail. No attestation: this is not a submission.
    """
    ctx = node_context(args, settings, prefix="opn-hazards-")
    verdict = pipeline.run_steps(ctx, steps=[ToolchainStep(), StatementStep(), HazardsStep()])
    summary = verdict.as_dict(settings.diagnostic_max_bytes)
    summary["hazards"] = ctx.data.get("hazards")
    sys.stdout.write(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    return EXIT_PASS if verdict.ok else EXIT_FAIL


def run_products(args: argparse.Namespace, settings: config.Settings) -> int:
    """F03: regenerate frontier.json, info.json, targets/index.json and every graph.json.

    Renders the checkout as it is, stamped with ``--commit`` (its committer time feeds
    ``ready_since``, R8). A defective graph (cycle, missing dep, ambiguous root) writes nothing
    and exits 1 with the problem named (R3). Library tags on a Mathlib-pinned graph need a scan
    inside the sandbox, which F10 wires; until then such a graph is refused here.
    """
    graph, commit = _checkout_and_commit(args.graph, args.commit)
    out_dir = args.out.resolve() if args.out is not None else graph
    claims_note = postmerge.refresh_claims(graph, getattr(args, "claims_url", None))
    try:
        products_ = products.generate(
            graph,
            rendered_from=commit,
            commit_time=graphmod.commit_timestamp(graph, commit),
        )
    except (graphmod.GraphError, schemas.SchemaError) as exc:
        sys.stdout.write(json.dumps({"ok": False, "error": str(exc)}) + "\n")
        sys.stderr.write(f"opn-gate: products not written: {exc}\n")
        return EXIT_FAIL
    if any(tg.spec["mathlib_sha"] is not None for tg in products_.targets):
        msg = "library tags on a Mathlib-pinned graph need the sandboxed scan (F10)"
        raise CliError(msg)
    written = products_.write(out_dir, write_meta=not args.no_meta and out_dir == graph)
    summary: dict[str, Any] = {
        "ok": True,
        "rendered_from": commit,
        "claims": claims_note or "refreshed",
        "written": [p.as_posix() for p in written],
        "files": sorted(p.as_posix() for p in products_.files),
    }
    sys.stdout.write(json.dumps(summary, indent=2) + "\n")
    return EXIT_PASS


def run_cache(args: argparse.Namespace, settings: config.Settings) -> int:
    return (
        run_cache_fetch(args)
        if args.cache_command == "fetch"
        else run_cache_publish(args, settings)
    )


def _spec_for(graph: Path, target_id: str) -> dict[str, Any]:
    spec_path = layout.gate_spec_path(graph, target_id)
    try:
        return schemas.load_json(spec_path, "gate-spec/v1")
    except schemas.SchemaError as exc:
        msg = f"cannot load {spec_path}: {exc}"
        raise CliError(msg) from exc


def run_cache_fetch(args: argparse.Namespace) -> int:
    """F10-R7 for the devcontainer and anyone else: fetch, verify, report. Exit 0 on a hit,
    1 otherwise — a miss is an answer, not an error."""
    graph = args.graph.resolve()
    if not graph.is_dir():
        msg = f"graph checkout not found: {graph}"
        raise CliError(msg)
    target_id = args.target or infer_target(graph)
    spec = _spec_for(graph, target_id)
    commit = args.commit
    if _git(graph, "rev-parse", "--is-inside-work-tree").returncode == 0:
        resolved = _git(graph, "rev-parse", "--verify", f"{commit}^{{commit}}").stdout.strip()
        commit = resolved or commit
    out_dir = _out_dir(args.out, "opn-cache-")
    result = cache.prepare(spec, graph, commit, out_dir / "olean-cache")
    doc = result.as_dict()
    doc["target"] = target_id
    doc["directory"] = str(out_dir / "olean-cache") if result.fetched else None
    sys.stdout.write(json.dumps(doc, indent=2) + "\n")
    return EXIT_PASS if result.status == "hit" else EXIT_FAIL


def run_cache_publish(args: argparse.Namespace, settings: config.Settings) -> int:
    """F10-R7, R8: the post-merge job's half — build every proved node's oleans from the merged
    tree (inside the image with ``--sandbox``, as the gate builds), pack them with a SHA-256
    manifest, and upload keyed by the merge commit. Without ``--bucket`` it stops after packing,
    which is how a laptop checks what a run would upload."""
    graph, commit = _checkout_and_commit(args.graph, args.commit)
    out_dir = _out_dir(args.out, "opn-cache-publish-")
    tree = export_tree(graph, commit, out_dir / "tree")
    target_id = args.target or infer_target(tree)
    spec = _spec_for(tree, target_id)
    workdir = out_dir / "work"
    tc: toolchain.Toolchain
    if args.sandbox:
        tag = args.image or ensure_image(spec, build=not args.no_build)
        tc = sandbox.SandboxToolchain(tag, sandbox.Caps.from_spec(spec), read_write=[workdir])
    else:
        try:
            tc = toolchain.LocalToolchain.from_settings(settings)
        except toolchain.ToolchainMissingError as exc:
            raise CliError(str(exc)) from exc
    try:
        built = cache.build(
            tree, target_id, tc, workdir, spec=spec, install=bool(args.install) and not args.sandbox
        )
        manifest, archive = cache.pack(built, graph_commit=commit, target_id=target_id, spec=spec)
    except (cache.CacheError, graphmod.GraphError, toolchain.ToolchainMissingError) as exc:
        sys.stdout.write(json.dumps({"ok": False, "error": str(exc)}) + "\n")
        sys.stderr.write(f"opn-gate: cache not published: {exc}\n")
        return EXIT_FAIL
    (out_dir / cache.MANIFEST).write_bytes(manifest)
    (out_dir / cache.ARCHIVE).write_bytes(archive)
    doc: dict[str, Any] = {
        "ok": True,
        "target": target_id,
        "commit": commit,
        "modules": sorted(built.modules),
        "archive_bytes": len(archive),
        "archive_sha256": cache.sha256(archive),
        "manifest": str(out_dir / cache.MANIFEST),
        "uploaded": False,
    }
    if args.bucket:
        try:
            store = objectstore.S3Store(args.bucket, prefix=args.prefix)
            cache.upload(store, target_id, commit, manifest, archive)
        except objectstore.ObjectStoreError as exc:
            doc["ok"] = False
            doc["error"] = str(exc)
            sys.stdout.write(json.dumps(doc, indent=2) + "\n")
            sys.stderr.write(f"opn-gate: cache built but not uploaded: {exc}\n")
            return EXIT_FAIL
        doc["uploaded"] = True
        doc["keys"] = [cache.archive_key(target_id, commit), cache.manifest_key(target_id, commit)]
    sys.stdout.write(json.dumps(doc, indent=2) + "\n")
    return EXIT_PASS


def run_sign(args: argparse.Namespace, settings: config.Settings) -> int:
    """Sign with the gate key read through config (C8); verify against the committed public key."""
    if not settings.gate_signing_key:
        msg = "OPN_GATE_SIGNING_KEY is not set"
        raise CliError(msg)
    doc = schemas.load_json(args.attestation)
    if doc.get("schema") not in attestation.ACCEPTED_SCHEMAS:
        msg = f"not an attestation: schema {doc.get('schema')!r}"
        raise CliError(msg)
    public_key = args.public_key.read_text(encoding="utf-8")
    s = signer.SshKeygenSigner()
    with tempfile.TemporaryDirectory(prefix="opn-gate-key-") as tmp:
        key_path = Path(tmp) / "gate"
        key_path.touch(mode=0o600)
        key_path.write_text(settings.gate_signing_key.rstrip("\n") + "\n", encoding="utf-8")
        signed = postmerge.sign_gate(doc, key_path=key_path, signer=s)
    if not postmerge.verify(signed, public_key, s):
        msg = f"signature does not verify against {args.public_key}; wrong key?"
        raise CliError(msg)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(schemas.canonical_json(signed))
    sys.stdout.write(json.dumps({"signed": str(args.out), "key_id": signed["signature"]["key_id"]}))
    sys.stdout.write("\n")
    return EXIT_PASS


# --- the curator's commands (F08-R9 to R12) ------------------------------------------------------


def _graph_and_target(args: argparse.Namespace) -> tuple[Path, str]:
    """The checkout and the target every curator command works on, both checked to exist."""
    graph: Path = args.graph.resolve()
    if not graph.is_dir():
        msg = f"graph checkout not found: {graph}"
        raise CliError(msg)
    target_id = args.target or infer_target(graph)
    if not layout.graph_nodes_dir(graph, target_id).is_dir():
        msg = f"target {target_id!r} has no nodes directory in {graph}"
        raise CliError(msg)
    return graph, target_id


def _curator_common(args: argparse.Namespace) -> tuple[Path, str, str]:
    graph, target_id = _graph_and_target(args)
    date = args.date or attestation.utc_now().strftime(DATE_FORMAT)
    try:  # a malformed flag is a usage error, not a schema refusal after the work
        datetime.strptime(date, DATE_FORMAT).replace(tzinfo=UTC)
    except ValueError:
        msg = f"--date must be a UTC timestamp like 2026-09-10T12:13:14Z, got {date!r}"
        raise CliError(msg) from None
    return graph, target_id, date


def _curator_branch(graph: Path, branch: str, message: str, written: Sequence[str]) -> None:
    """A branch and one commit holding what a command wrote — the curator's pull request is
    then `git push` and `gh pr create`, under the curator's own credentials, which the gate
    never holds (C8; F08-Q17)."""
    if _git(graph, "rev-parse", "--is-inside-work-tree").returncode != 0:
        msg = f"--branch needs a git checkout; {graph} is not one"
        raise CliError(msg)
    for step in (
        ["checkout", "-q", "-b", branch],
        ["add", "--", *written],
        ["commit", "-q", "-m", message],
    ):
        proc = _git(graph, *step)
        if proc.returncode != 0:
            msg = f"git {step[0]} failed: {proc.stderr.strip()}"
            raise CliError(msg)


def _emit_curator(doc: dict[str, Any], graph: Path, branch: str | None, message: str) -> int:
    if branch:
        _curator_branch(graph, branch, message, [str(p) for p in doc.get("written", [])])
        doc["branch"] = branch
        doc["next"] = f"git push -u origin {branch} && gh pr create --fill"
    sys.stdout.write(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    return EXIT_PASS


def run_revise(args: argparse.Namespace, settings: config.Settings) -> int:
    graph, target_id, date = _curator_common(args)
    statement = _read_flag_file(args.statement, "--statement")
    if not args.request.is_file():
        msg = f"--request {args.request} is not a file"
        raise CliError(msg)
    revision = curator.revise(
        graph, target_id, args.node_id, statement, args.request, author=args.author, date=date
    )
    doc = {"ok": True, **revision.as_dict()}
    return _emit_curator(doc, graph, args.branch, f"revise: {args.node_id} -> {revision.new_id}")


def run_consolidate(args: argparse.Namespace, settings: config.Settings) -> int:
    graph, target_id, date = _curator_common(args)
    defeq: curator.Defeq | None = None
    if not args.no_toolchain:
        spec_path = layout.gate_spec_path(graph, target_id)
        try:
            spec = schemas.load_json(spec_path, "gate-spec/v1")
        except schemas.SchemaError as exc:
            msg = f"cannot load {spec_path}: {exc}"
            raise CliError(msg) from exc
        out_dir = _out_dir(args.out, "opn-consolidate-")
        workdir = out_dir / "work"
        tc: toolchain.Toolchain
        if args.sandbox:
            tag = args.image or ensure_image(spec, build=not args.no_build)
            tc = sandbox.SandboxToolchain(tag, sandbox.Caps.from_spec(spec), read_write=[workdir])
        else:
            try:
                tc = toolchain.LocalToolchain.from_settings(settings)
            except toolchain.ToolchainMissingError as exc:
                raise CliError(str(exc)) from exc
        ctx = RunContext(
            graph_root=graph,
            claim=Claim(target_id, args.keep),
            spec=spec,
            gate_spec_hash=schemas.content_hash(spec_path.read_bytes()),
            changes=None,
            workdir=workdir,
            toolchain=tc,
            settings=settings,
            install_toolchain=bool(args.install) and not args.sandbox,
        )

        def defeq(kept: layout.Node, dropped: layout.Node) -> bool:
            return curator.statements_defeq(ctx, kept, dropped)

    record = curator.consolidate(
        graph, target_id, args.keep, args.drop, author=args.author, date=date, defeq=defeq
    )
    written = [record.resolve().relative_to(graph).as_posix()]
    doc = {"ok": True, "keep": args.keep, "drop": args.drop, "written": written}
    return _emit_curator(doc, graph, args.branch, f"consolidate: {args.drop} into {args.keep}")


def run_status(args: argparse.Namespace, settings: config.Settings) -> int:
    graph, target_id, date = _curator_common(args)
    now = attestation.utc_now()
    record = curator.declare_status(
        graph,
        target_id,
        args.ref,
        args.status,
        args.cause,
        author=args.author,
        date=date,
        now=now,
        last_merge=last_progress_merge(graph, target_id),
        k=args.k,
        n_days=args.n,
    )
    written = [record.resolve().relative_to(graph).as_posix()]
    doc = {"ok": True, "ref": args.ref, "status": args.status, "written": written}
    return _emit_curator(doc, graph, args.branch, f"status: {args.ref} {args.status}")


def last_progress_merge(graph: Path, target_id: str) -> datetime | None:
    """When the target's nodes last changed on ``main``'s history — the latest commit touching
    them, which is a merge or the bot's products commit (D-33 a). ``None`` for a bare tree."""
    if _git(graph, "rev-parse", "--is-inside-work-tree").returncode != 0:
        return None
    proc = _git(graph, "log", "-1", "--format=%cI", "--", f"targets/{target_id}/nodes")
    when = proc.stdout.strip()
    if proc.returncode != 0 or not when:
        return None
    return datetime.fromisoformat(when).astimezone(UTC)


def run_missing_library(args: argparse.Namespace, settings: config.Settings) -> int:
    graph, target_id = _graph_and_target(args)
    report = curator.missing_library_report(graph, target_id, threshold=args.threshold)
    doc = {
        "target": target_id,
        "threshold": args.threshold,
        "lemmas": [m.as_dict() for m in report],
        "created": [],  # D-13, F08-Q3: the curator proposes; nothing is created here
    }
    sys.stdout.write(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    return EXIT_PASS


def run_ledger(args: argparse.Namespace, settings: config.Settings) -> int:
    """F08-R13: after a proposal merges, the proposer's statement line — for a variant or a
    speculative crux, never a hole (D-31) and never a revision (D-19)."""
    graph, commit = _checkout_and_commit(args.graph, args.commit)
    classification = modes.classify(commit_changes(graph, commit), author=settings.pr_author)
    roles = {loc.role for loc in classification.located}
    nothing: dict[str, Any] = {"earned": False, "commit": commit}
    if classification.mode != "proposal" or classification.admit is None or "node" not in roles:
        nothing["reason"] = f"not a merged node proposal (mode {classification.mode!r})"
        sys.stdout.write(json.dumps(nothing, indent=2) + "\n")
        return EXIT_PASS
    target_id, node_id = str(classification.target_id), classification.admit
    meta = schemas.load_yaml(layout.graph_nodes_dir(graph, target_id) / node_id / "META.yaml")
    identity = proposer_of(graph, commit)
    entry = ledger.statement_entry(
        identity=identity,
        target=target_id,
        node=node_id,
        origin=str(meta.get("origin")),
        merge_commit=commit,
        date=graphmod.commit_timestamp(graph, commit),
        tutorial=bool(meta.get("tutorial", False)),
        supersedes=str(meta["supersedes"]) if meta.get("supersedes") else None,
    )
    if entry is None:
        nothing["reason"] = f"{node_id} ({meta.get('origin')}) earns no statement line (D-19, D-31)"
        sys.stdout.write(json.dumps(nothing, indent=2) + "\n")
        return EXIT_PASS
    try:
        path = ledger.record(graph, identity, entry)
    except schemas.SchemaError as exc:
        nothing["reason"] = f"identity {identity!r} cannot hold a ledger: {exc}"
        sys.stdout.write(json.dumps(nothing, indent=2) + "\n")
        return EXIT_PASS
    assert path is not None
    doc = {
        "earned": True,
        "identity": identity,
        "node": node_id,
        "line": entry.line,
        "written": path.resolve().relative_to(graph).as_posix(),
    }
    sys.stdout.write(json.dumps(doc, indent=2) + "\n")
    return EXIT_PASS


def proposer_of(graph: Path, commit: str) -> str:
    """The ledger identity behind a merge: the author of the pull request's commit (F07-R2 puts
    the pseudonym there) — the second parent's for a merge commit, the commit's own otherwise."""
    head = (
        f"{commit}^2"
        if _git(graph, "rev-parse", "--verify", "--quiet", f"{commit}^2").returncode == 0
        else commit
    )
    return _git(graph, "log", "-1", "--format=%an", head).stdout.strip()


def _checkout_and_commit(graph_arg: Path, ref: str) -> tuple[Path, str]:
    graph = graph_arg.resolve()
    if _git(graph, "rev-parse", "--is-inside-work-tree").returncode != 0:
        msg = f"{graph} is not a git checkout"
        raise CliError(msg)
    commit = _git(graph, "rev-parse", "--verify", f"{ref}^{{commit}}").stdout.strip()
    if not commit:
        msg = f"unknown commit {ref!r}"
        raise CliError(msg)
    return graph, commit


def _out_dir(out: Path | None, prefix: str) -> Path:
    out_dir = (out or Path(tempfile.mkdtemp(prefix=prefix))).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def _sandboxed_context(  # noqa: PLR0913 — one argument per CLI flag
    graph: Path,
    commit: str,
    out_dir: Path,
    *,
    target: str | None,
    node: str,
    settings: config.Settings,
    image: str | None,
    no_build: bool,
) -> RunContext:
    """Export the tree at ``commit`` and build a RunContext whose toolchain is the sandbox."""
    tree = export_tree(graph, commit, out_dir / "tree")
    target_id = target or infer_target(tree)
    spec_path = layout.gate_spec_path(tree, target_id)
    try:
        spec = schemas.load_json(spec_path, "gate-spec/v1")
    except schemas.SchemaError as exc:
        msg = f"cannot load {spec_path}: {exc}"
        raise CliError(msg) from exc
    tag = image or ensure_image(spec, build=not no_build)
    node_dir = layout.graph_nodes_dir(tree, target_id) / node
    workdir = out_dir / "work"
    tc = sandbox.SandboxToolchain(
        tag, sandbox.Caps.from_spec(spec), read_only=[node_dir], read_write=[workdir]
    )
    return RunContext(
        graph_root=tree,
        claim=Claim(target_id, node),
        spec=spec,
        gate_spec_hash=schemas.content_hash(spec_path.read_bytes()),
        changes=commit_changes(graph, commit),
        workdir=workdir,
        toolchain=tc,
        settings=settings,
    )


def export_tree(graph: Path, commit: str, dest: Path) -> Path:
    """The graph's tree at ``commit`` as plain files (no .git), via git archive."""
    dest.mkdir(parents=True, exist_ok=True)
    archive = subprocess.run(
        ["git", "-C", str(graph), "archive", "--format=tar", commit],
        capture_output=True,
        check=True,
        env=git_environment(),
    )
    subprocess.run(["tar", "-x", "-C", str(dest)], input=archive.stdout, check=True)
    return dest


def commit_changes(graph: Path, commit: str) -> list[Change]:
    """What ``commit`` changed against its first parent (a merge: the whole PR)."""
    parent = _git(graph, "rev-parse", "--verify", "--quiet", f"{commit}^")
    if parent.returncode != 0:
        return []
    diff = _git(graph, "diff", "--name-status", "--no-renames", f"{commit}^", commit)
    return paths.changes_from_name_status(diff.stdout)


def ensure_image(spec: dict[str, Any], *, build: bool) -> str:
    """The image every sandboxed run uses, from the graph's gate-spec alone (F10-R5, Q10).

    A graph that pins ``devcontainer_ref`` names the published image by digest, and that digest
    is what the authoritative gate, the precheck job, ``reproduce.sh`` and the devcontainer all
    run — pulled once if absent, never built. A graph that pins none (the fixtures, a graph
    before its first pin) gets the image built from ``gate/Dockerfile`` for its toolchain, as
    before; ``--no-build`` then requires it to be present already.
    """
    ref = spec.get("devcontainer_ref")
    if isinstance(ref, str) and ref:
        if sandbox.image_exists(ref):
            return ref
        log.info("pulling the pinned image %s", ref)
        try:
            return sandbox.pull_image(ref)
        except sandbox.SandboxError as exc:
            raise CliError(str(exc)) from exc
    lean_toolchain = str(spec["lean_toolchain"])
    tag = sandbox.image_tag(lean_toolchain)
    if sandbox.image_exists(tag):
        return tag
    if not build:
        msg = f"sandbox image {tag} is not present; build it from gate/Dockerfile"
        raise CliError(msg)
    log.info("building sandbox image %s", tag)
    return sandbox.build_image(GATE_DIR, lean_toolchain)


def infer_target(graph: Path) -> str:
    targets = sorted(p.name for p in (graph / "targets").iterdir() if p.is_dir())
    if len(targets) != 1:
        msg = f"--target is required; graph has targets {targets}"
        raise CliError(msg)
    return targets[0]


def _git(graph: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """``git -C <graph> ...`` on the graph checkout and nothing else: the repository variables
    git exports to a hook are dropped, or a pre-commit hook running the gate from a worktree
    would see ``--branch`` check out and stage in the repository that ran the hook (F08-Q18)."""
    return subprocess.run(
        ["git", "-C", str(graph), *args],
        capture_output=True,
        text=True,
        check=False,
        env=git_environment(),
    )


def git_environment() -> dict[str, str]:
    return config.child_environment(drop=config.GIT_REPO_VARIABLES)


def worktree_changes(graph: Path, base: str | None) -> list[Change] | None:
    """Tracked changes against ``base`` plus untracked files; ``None`` when not a git checkout."""
    if _git(graph, "rev-parse", "--is-inside-work-tree").returncode != 0:
        log.warning("%s is not a git checkout; step 2 runs without a diff", graph)
        return None
    ref = base or "HEAD"
    diff = _git(graph, "diff", "--name-status", "--no-renames", ref, "--")
    if diff.returncode != 0:
        msg = f"git diff against {ref!r} failed: {diff.stderr.strip()}"
        raise CliError(msg)
    changes = paths.changes_from_name_status(diff.stdout)
    untracked = _git(graph, "ls-files", "--others", "--exclude-standard")
    changes.extend(Change("A", line.strip()) for line in untracked.stdout.splitlines() if line)
    return changes


def clean_head(graph: Path) -> str | None:
    """HEAD's sha when the tree is exactly that commit; ``None`` for a dirty or non-git tree."""
    if _git(graph, "rev-parse", "--is-inside-work-tree").returncode != 0:
        return None
    status = _git(graph, "status", "--porcelain")
    if status.stdout.strip():
        return None
    head = _git(graph, "rev-parse", "HEAD")
    return head.stdout.strip() if head.returncode == 0 else None


if __name__ == "__main__":
    sys.exit(main())
