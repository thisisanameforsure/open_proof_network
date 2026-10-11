"""F22-T14: outline a graph's merged artifacts again and check that no published step id moved.

Explainers anchor on outline step ids (F20-R3), so a change to the extractor may add steps and
fields but never drop or move a step a published outline has. This re-extracts every artifact
that has an outline at ``--ref`` with *this* checkout's gate, in the given step-3 image, and
compares each new outline with the published one (``outline.lost_ids``)::

    uv run python gate/tools/check_outline_ids.py --graph <graph checkout> --ref origin/main \\
        --target erdos-1050 --image <image whose OPN_LEAN_PKG_BIN holds this gate's opn-outline> \\
        --out <dir>

The image must carry the target's Mathlib and *this* checkout's Lean programs: the published
image carries the pinned gate's, which would compare the old extractor with itself. One JSON
document on stdout: per artifact, the ids lost or moved, the steps added, and the case steps
whose hypotheses changed; exit 1 when any id was lost or any artifact could not be outlined.
Reads the graph with ``git archive`` and writes only under ``--out``.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from opn_gate import cli, config, outline, outline_graph, sandbox, toolchain


def _steps(doc: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    stack = list(doc.get("steps") or [])
    while stack:
        step = stack.pop()
        out[str(step["id"])] = step
        stack.extend(step.get("children") or [])
    return out


def _hyps(step: dict[str, Any]) -> list[str]:
    return [str(h["name"]) for h in (step.get("goal") or {}).get("hypotheses") or []]


def compare(old: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    """What changed between a published outline and the same artifact outlined again."""
    before, after = _steps(old), _steps(new)
    return {
        "lost": outline.lost_ids(old, new),
        "added": sorted(set(after) - set(before)),
        "case_hypotheses": {
            sid: {"was": _hyps(step), "now": _hyps(after[sid])}
            for sid, step in sorted(before.items())
            if step["kind"] == "case" and sid in after and _hyps(step) != _hyps(after[sid])
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--graph", type=Path, required=True)
    parser.add_argument("--ref", default="origin/main")
    parser.add_argument("--target", action="append", required=True)
    parser.add_argument("--image", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    graph, commit = cli._checkout_and_commit(args.graph, args.ref)
    out = args.out.resolve()
    if out.exists():
        shutil.rmtree(out)
    tree = cli.export_tree(graph, commit, out / "tree")
    published: dict[tuple[str, str], dict[str, Any]] = {}
    for target in args.target:
        directory = tree / "targets" / target / outline.OUTLINES_DIR
        for path in sorted(directory.glob("*.json")) if directory.is_dir() else []:
            published[(target, path.stem)] = json.loads(path.read_text(encoding="utf-8"))
        if directory.is_dir():
            shutil.rmtree(directory)  # so every artifact is outlined again

    def toolchain_for(spec: Any, workdir: Path) -> toolchain.Toolchain:
        workdir.mkdir(parents=True, exist_ok=True)
        return sandbox.SandboxToolchain(
            args.image, sandbox.Caps.from_spec(dict(spec)), read_write=[workdir]
        )

    report = outline_graph.run(
        tree,
        args.target,
        dest=out / "new",
        work=out / "work",
        toolchain_for=toolchain_for,
        gate="0" * 40,
        caps=outline.Caps.from_settings(config.load()),
    )
    artifacts: list[dict[str, Any]] = []
    for (target, digest), old in sorted(published.items()):
        path = out / "new" / "targets" / target / outline.OUTLINES_DIR / f"{digest}.json"
        if not path.is_file():
            artifacts.append({"target": target, "artifact": digest, "outlined": False})
            continue
        new = json.loads(path.read_text(encoding="utf-8"))
        artifacts.append(
            {"target": target, "artifact": digest, "node": old["node"], "outlined": True}
            | compare(old, new)
        )
    lost = sum(len(a.get("lost") or []) for a in artifacts)
    missing = sum(1 for a in artifacts if not a["outlined"])
    doc = {
        "commit": commit,
        "image": args.image,
        "published": len(published),
        "outlined_again": len(published) - missing,
        "ids_lost_or_moved": lost,
        "failed": [e.as_dict() for e in report.failed],
        "artifacts": artifacts,
    }
    sys.stdout.write(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    return 1 if lost or missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
