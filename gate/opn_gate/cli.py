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
    config,
    layout,
    paths,
    pipeline,
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
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    settings = config.load()
    logging.basicConfig(level=settings.log_level, format="%(levelname)s %(name)s: %(message)s")
    try:
        if args.command == "pregate":
            return run_pregate(args, settings)
        if args.command == "reproduce":
            return run_reproduce(args, settings)
    except CliError as exc:
        sys.stderr.write(f"opn-gate: {exc}\n")
        return EXIT_ERROR
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
        schemas.validate(doc, "attestation/v1")
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
    graph: Path = args.graph.resolve()
    if _git(graph, "rev-parse", "--is-inside-work-tree").returncode != 0:
        msg = f"{graph} is not a git checkout"
        raise CliError(msg)
    commit = _git(graph, "rev-parse", "--verify", f"{args.commit}^{{commit}}").stdout.strip()
    if not commit:
        msg = f"unknown commit {args.commit!r}"
        raise CliError(msg)
    out_dir: Path = (args.out or Path(tempfile.mkdtemp(prefix="opn-reproduce-"))).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    tree = export_tree(graph, commit, out_dir / "tree")
    target_id = args.target or infer_target(tree)
    claim = Claim(target_id, args.node)
    spec_path = layout.gate_spec_path(tree, target_id)
    try:
        spec = schemas.load_json(spec_path, "gate-spec/v1")
    except schemas.SchemaError as exc:
        msg = f"cannot load {spec_path}: {exc}"
        raise CliError(msg) from exc

    image = args.image or ensure_image(str(spec["lean_toolchain"]), build=not args.no_build)
    node_dir = layout.graph_nodes_dir(tree, target_id) / args.node
    workdir = out_dir / "work"
    tc = sandbox.SandboxToolchain(
        image, sandbox.Caps.from_spec(spec), read_only=[node_dir], read_write=[workdir]
    )
    ctx = RunContext(
        graph_root=tree,
        claim=claim,
        spec=spec,
        gate_spec_hash=schemas.content_hash(spec_path.read_bytes()),
        changes=commit_changes(graph, commit),
        workdir=workdir,
        toolchain=tc,
        settings=settings,
    )
    verdict = pipeline.run_submission(ctx)
    doc = attestation.build(ctx, verdict, graph_commit=commit)
    code = emit(verdict, doc, out_dir, settings)
    if args.compare is not None:
        committed = schemas.load_json(args.compare, "attestation/v1")
        differing = attestation.compare(committed, attestation.with_step9(doc, committed))
        result = {"identical": not differing, "differing_fields": differing}
        sys.stdout.write(json.dumps(result) + "\n")
        return EXIT_PASS if not differing else EXIT_FAIL
    return code


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
