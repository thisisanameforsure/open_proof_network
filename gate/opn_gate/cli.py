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
from pathlib import Path
from typing import Any

from opn_gate import (
    attestation,
    bounce,
    config,
    layout,
    paths,
    pipeline,
    postmerge,
    sandbox,
    schemas,
    signer,
    toolchain,
)
from opn_gate.paths import Change, Claim
from opn_gate.steps.base import RunContext

GATE_DIR = Path(__file__).resolve().parents[1]

log = logging.getLogger("opn_gate")

EXIT_PASS = 0
EXIT_FAIL = 1
EXIT_ERROR = 2
EXIT_BOUNCED = 3


class CliError(Exception):
    """A problem with the invocation itself, reported before any verdict exists."""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="opn-gate", description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)

    pre = sub.add_parser("pregate", help="run gate steps 1, 2, 4, 5 locally on one node")
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
    rep.add_argument("--out", type=Path, help="output directory (default: a fresh temp dir)")
    rep.add_argument("--compare", type=Path, help="committed attestation to compare against")
    rep.add_argument("--image", help="sandbox image tag (default: built from gate/Dockerfile)")
    rep.add_argument("--no-build", action="store_true", help="fail if the image is not present")

    gate = sub.add_parser("gate", help="the authoritative run on a pull request (gate.yml)")
    gate.add_argument("--graph", required=True, type=Path, help="checkout at the PR merge commit")
    gate.add_argument("--base", required=True, help="the pull request's base sha")
    gate.add_argument("--head", default="HEAD", help="the commit to check (default HEAD)")
    gate.add_argument("--target", required=True)
    gate.add_argument("--node", required=True)
    gate.add_argument("--pr-body-file", required=True, type=Path)
    gate.add_argument("--out", type=Path)
    gate.add_argument("--image")
    gate.add_argument("--no-build", action="store_true")

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
    post.add_argument("--target", required=True)
    post.add_argument("--node", required=True)
    post.add_argument("--out", type=Path)
    post.add_argument("--image")
    post.add_argument("--no-build", action="store_true")

    sign = sub.add_parser("sign", help="sign an attestation with the gate key from the environment")
    sign.add_argument("--attestation", required=True, type=Path)
    sign.add_argument("--public-key", required=True, type=Path, help="keys/gate.pub to verify")
    sign.add_argument("--out", required=True, type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    settings = config.load()
    logging.basicConfig(level=settings.log_level, format="%(levelname)s %(name)s: %(message)s")
    commands = {
        "pregate": run_pregate,
        "reproduce": run_reproduce,
        "gate": run_gate,
        "postmerge": run_postmerge,
        "sign": run_sign,
    }
    try:
        return commands[args.command](args, settings)
    except CliError as exc:
        sys.stderr.write(f"opn-gate: {exc}\n")
        return EXIT_ERROR


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
    verdict = pipeline.run_submission(ctx)
    doc = attestation.build(
        ctx,
        verdict,
        graph_commit=None if args.no_diff else clean_head(graph),
        tooling={"model": args.model, "harness": args.harness},
    )
    if args.sign is not None:
        sig = signer.SshKeygenSigner().sign(attestation.signed_bytes(doc), args.sign, "contributor")
        doc["signature"] = {
            "kind": sig.kind,
            "key_id": sig.key_id,
            "value": sig.value,
            "timestamp": doc["signature"]["timestamp"],
        }
        schemas.validate(doc, attestation.SCHEMA)
    return emit(verdict, doc, out_dir, settings)


def emit(
    verdict: pipeline.Verdict, doc: dict[str, Any], out_dir: Path, settings: config.Settings
) -> int:
    verdict_doc = verdict.as_dict(settings.diagnostic_max_bytes)
    (out_dir / "verdict.json").write_bytes(schemas.canonical_json(verdict_doc))
    (out_dir / "attestation.json").write_bytes(schemas.canonical_json(doc))
    summary = dict(verdict_doc)
    summary["attestation"] = str(out_dir / "attestation.json")
    summary["verdict_file"] = str(out_dir / "verdict.json")
    sys.stdout.write(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    if verdict.verdict == "pass":
        return EXIT_PASS
    if verdict.verdict == "bounced":
        return EXIT_BOUNCED
    return EXIT_FAIL


# --- reproduce ----------------------------------------------------------------------------------


def run_reproduce(args: argparse.Namespace, settings: config.Settings) -> int:
    graph, commit = _checkout_and_commit(args.graph, args.commit)
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
    if args.compare is not None:
        committed = schemas.load_json(args.compare)
        differing = attestation.compare(committed, attestation.with_step9(doc, committed))
        result = {"identical": not differing, "differing_fields": differing}
        sys.stdout.write(json.dumps(result) + "\n")
        return EXIT_PASS if not differing else EXIT_FAIL
    return code


def run_gate(args: argparse.Namespace, settings: config.Settings) -> int:
    """The authoritative run: bounce rule, then steps 1, 2, 4, 5 in the sandbox (runner hosted)."""
    graph, head = _checkout_and_commit(args.graph, args.head)
    base = _git(graph, "rev-parse", "--verify", f"{args.base}^{{commit}}").stdout.strip()
    if not base:
        msg = f"unknown base {args.base!r}"
        raise CliError(msg)
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
        pr_body=args.pr_body_file.read_text(encoding="utf-8"),
        accepted_signatures=tuple(ctx.spec["accepted_precheck_signatures"]),
        max_age_s=int(ctx.spec["precheck_max_age_s"]),
        now=attestation.utc_now(),
        node_id=args.node,
        statement_hash=schemas.content_hash(statement.read_bytes()) if statement.is_file() else "",
    )
    verdict = pipeline.run_submission(ctx, precheck=policy)
    doc = attestation.build(ctx, verdict, graph_commit=head)
    return emit(verdict, doc, out_dir, settings)


def run_postmerge(args: argparse.Namespace, settings: config.Settings) -> int:
    """Re-derive on the merge commit and record step 9; signing is the separate `sign` step."""
    graph, commit = _checkout_and_commit(args.graph, args.commit)
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
    try:
        review = postmerge.review_block(
            args.review_kind, reviewer=args.reviewer, reference=args.review_reference
        )
    except ValueError as exc:
        raise CliError(str(exc)) from exc
    doc = postmerge.record_step9(doc, merge_commit=commit, review=review)
    code = emit(verdict, doc, out_dir, settings)
    if code != EXIT_PASS:
        sys.stderr.write("opn-gate: the merged commit does not pass the gate; not attesting\n")
    return code


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
    tag = image or ensure_image(str(spec["lean_toolchain"]), build=not no_build)
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


def ensure_image(lean_toolchain: str, *, build: bool) -> str:
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
    return subprocess.run(
        ["git", "-C", str(graph), *args], capture_output=True, text=True, check=False
    )


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
