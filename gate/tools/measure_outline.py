"""F19-T1: measure ``opn-outline`` against step 4, so Q2 is decided by evidence.

Two modes, each printing one JSON document:

``graph``  a merged proof on a graph checkout, as the gate would see it::

    uv run python gate/tools/measure_outline.py graph --graph <checkout> --target erdos-1050 \\
        --node <node-id> [--out <dir>]

    Steps 1, 2 and 4 build and replay the node's ``Proof.lean`` exactly as the gate does (the
    same steps ``opn-gate footprints`` runs), timed; then ``opn-outline`` is run over the staged
    proof with the build on its search path, timed. For a Mathlib target this needs the pinned
    toolchain and Mathlib checkout, so run it **inside the pinned image** (the graph's
    ``devcontainer_ref``), where ``OPN_LEAN_PKG_BIN`` and ``OPN_MATHLIB_HOME`` already point at
    them, e.g.::

        docker run --rm -v <checkout>:/graph:ro -v $PWD:/net -w /net <devcontainer_ref> \\
            uv run python gate/tools/measure_outline.py graph --graph /graph \\
            --target erdos-1050 --node <node-id> --out /tmp/measure

``file``   one Lean file with the toolchain on this machine (the lean-tier fixtures)::

    uv run python gate/tools/measure_outline.py file --file F.lean --module F --decl D

Each phase runs in a child process of its own, so the peak resident memory reported for it
(``getrusage(RUSAGE_CHILDREN).ru_maxrss`` of that child: the largest of the processes it waited
for, ``lean``/``leanchecker``/``opn-outline`` under ``elan``) belongs to that phase alone. Wall
time is the child's own clock around the work. Nothing is written outside ``--out``.

The 20% line Q2 names is the owner's to read against these numbers; this script decides nothing.
"""

from __future__ import annotations

import argparse
import json
import resource
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from opn_gate import config, layout, outline, schemas
from opn_gate.paths import Claim
from opn_gate.steps.base import RunContext
from opn_gate.toolchain import LocalToolchain, OutlineRequest


def _peak_mib() -> float:
    """The largest resident set of any child this process has waited for, in MiB."""
    raw = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    # Linux reports KiB, macOS bytes.
    return raw / 1024 / 1024 if sys.platform == "darwin" else raw / 1024


def _toolchain(settings: config.Settings) -> LocalToolchain:
    return LocalToolchain.from_settings(settings)


def child_file(args: argparse.Namespace) -> dict[str, Any]:
    """``opn-outline`` over one file, through the gate's own seam."""
    settings = config.load()
    tc = _toolchain(settings)
    pinned = tc.resolve(args.toolchain, mathlib_sha=args.mathlib_sha)
    caps = outline.Caps.from_settings(settings)
    req = OutlineRequest(
        file=Path(args.file),
        module=args.module,
        decl=args.decl,
        automation=caps.automation,
        doc_modules=layout.LIBRARY_PREFIXES,
    )
    started = time.monotonic()
    result = tc.outline(pinned, req, [Path(p) for p in args.search_path], timeout_s=caps.timeout_s)
    wall = time.monotonic() - started
    size = len(json.dumps(result.doc).encode()) if result.ok else 0
    return {
        "phase": "outline",
        "ok": result.ok,
        "error": None if result.ok else (result.error or result.output)[:2000],
        "wall_s": round(wall, 2),
        "peak_rss_mib": round(_peak_mib(), 1),
        "output_bytes": size,
        "top_level_steps": len(result.doc.get("steps", [])) if result.ok else None,
    }


def child_step4(args: argparse.Namespace) -> dict[str, Any]:
    """Steps 1, 2 and 4 over the node's merged proof, as ``opn-gate footprints`` runs them."""
    from opn_gate import footprints, pipeline  # noqa: PLC0415

    settings = config.load()
    graph = Path(args.graph)
    spec_path = layout.gate_spec_path(graph, args.target)
    spec = schemas.load_json(spec_path, "gate-spec/v1")
    workdir = Path(args.out) / "work"
    ctx = RunContext(
        graph_root=graph,
        claim=Claim(args.target, args.node),
        spec=spec,
        gate_spec_hash=schemas.content_hash(spec_path.read_bytes()),
        changes=None,
        workdir=workdir,
        toolchain=_toolchain(settings),
        settings=settings,
    )
    steps = [s for s in footprints.steps() if s.number in (1, 2, 4)]
    started = time.monotonic()
    verdict = pipeline.run_steps(ctx, steps=steps)
    wall = time.monotonic() - started
    staged = ctx.data.get("staged")
    node = ctx.node
    proof = None if staged is None else staged.node_dir(args.node) / "Proof.lean"
    return {
        "phase": "steps 1, 2 and 4",
        "verdict": verdict.verdict,
        "first_failing_step": verdict.first_failing_step,
        "wall_s": round(wall, 2),
        "peak_rss_mib": round(_peak_mib(), 1),
        "toolchain": spec["lean_toolchain"],
        "mathlib_sha": spec.get("mathlib_sha"),
        "proof": None if proof is None else str(proof),
        "proof_lines": None if proof is None else len(proof.read_text("utf-8").splitlines()),
        "module": layout.node_module(args.node, "Proof"),
        "decl": None if node is None else node.statement.decl_name,
        "build": None if staged is None else str(staged.build),
    }


def _run_child(argv: list[str]) -> dict[str, Any]:
    proc = subprocess.run(
        [sys.executable, __file__, *argv], capture_output=True, text=True, check=False
    )
    lines = [ln for ln in proc.stdout.splitlines() if ln.strip()]
    if proc.returncode != 0 or not lines:
        return {"ok": False, "exit": proc.returncode, "stderr": proc.stderr[-3000:]}
    doc: dict[str, Any] = json.loads(lines[-1])
    return doc


def graph_mode(args: argparse.Namespace) -> dict[str, Any]:
    out = Path(args.out or tempfile.mkdtemp(prefix="opn-measure-outline-"))
    base = ["--graph", args.graph, "--target", args.target, "--node", args.node, "--out", str(out)]
    step4 = _run_child(["_step4", *base])
    if step4.get("verdict") != "pass" or not step4.get("proof"):
        return {"step4": step4, "outline": None, "note": "step 4 did not pass; nothing measured"}
    pinned = ["--toolchain", step4["toolchain"]]
    if step4.get("mathlib_sha"):
        pinned += ["--mathlib-sha", step4["mathlib_sha"]]
    measured = _run_child(
        [
            "_file",
            "--file",
            step4["proof"],
            "--module",
            step4["module"],
            "--decl",
            step4["decl"],
            "--search-path",
            step4["build"],
            *pinned,
        ]
    )
    ratio = None
    if measured.get("ok") and step4["wall_s"]:
        ratio = round(measured["wall_s"] / step4["wall_s"], 3)
    return {"step4": step4, "outline": measured, "outline_over_step4_wall": ratio}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    sub = p.add_subparsers(dest="mode", required=True)
    g = sub.add_parser("graph")
    g.add_argument("--graph", required=True)
    g.add_argument("--target", required=True)
    g.add_argument("--node", required=True)
    g.add_argument("--out")
    for name in ("file", "_file"):
        f = sub.add_parser(name)
        f.add_argument("--file", required=True)
        f.add_argument("--module", required=True)
        f.add_argument("--decl", required=True)
        f.add_argument("--search-path", action="append", default=[])
        f.add_argument(
            "--toolchain",
            default=(Path(__file__).resolve().parents[1] / "lean" / "lean-toolchain")
            .read_text()
            .strip(),
        )
        f.add_argument("--mathlib-sha")
    s = sub.add_parser("_step4")
    for name in ("--graph", "--target", "--node", "--out"):
        s.add_argument(name, required=True)
    args = p.parse_args(argv)
    if args.mode == "graph":
        doc = graph_mode(args)
    elif args.mode == "_step4":
        doc = child_step4(args)
    elif args.mode == "_file":
        doc = child_file(args)
    else:
        rest = [
            "--file", args.file, "--module", args.module, "--decl", args.decl,
            "--toolchain", args.toolchain,
            *(["--mathlib-sha", args.mathlib_sha] if args.mathlib_sha else []),
            *[x for sp in args.search_path for x in ("--search-path", sp)],
        ]  # fmt: skip
        doc = _run_child(["_file", *rest])
    sys.stdout.write(json.dumps(doc) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
