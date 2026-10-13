"""F20-T16 (Q21): which of a target's current glosses do not open with math.

The gloss contract is math first: a gloss opens with the statement in LaTeX (``$$…$$`` or
``$…$``), then the Lean conventions that change its meaning, then prose. That is guidance, not a
gate rule (D-3: prose is unverified), so nothing refuses a gloss that does not; this lists them::

    uv run python gate/tools/check_gloss_form.py --graph <graph checkout> --target erdos-1094

It reads ``targets/<id>/glosses.json`` and, for every gloss chain (statement, witness, relation
or definition module; explainers are not glosses) with a current version, that version's file,
and asks ``glosses.opens_with_math`` of its body. One JSON document on stdout: the number of
current versions read and, for each that does not open with math, its subject, path and first
line. Exit 1 when any does not, 2 when the target's ``glosses.json`` or a version's file cannot
be read. It reads the working tree as it is: to measure a commit, check that commit out (a
detached worktree) and point ``--graph`` at it.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from opn_gate import glosses


def current_glosses(target_dir: Path, doc: dict[str, Any]) -> list[dict[str, Any]]:
    """Every gloss chain's current version: its subject and its path under the target."""
    out = []
    for subject in doc.get("subjects") or []:
        if subject.get("record") != "gloss":
            continue
        for chain in subject.get("chains") or []:
            current = chain.get("current")
            if current is None:
                continue
            [version] = [v for v in chain["versions"] if v["hash"] == current]
            out.append(
                {
                    "kind": subject["kind"],
                    "node": subject.get("node"),
                    "module": subject.get("module"),
                    "hash": current,
                    "path": version["path"],
                    "file": target_dir / version["path"],
                }
            )
    return out


def check(graph: Path, target_id: str) -> dict[str, Any]:
    """The report; raises ``OSError`` or ``ValueError`` when a file cannot be read."""
    target_dir = graph / "targets" / target_id
    doc = json.loads((target_dir / "glosses.json").read_text(encoding="utf-8"))
    found = current_glosses(target_dir, doc)
    bad = []
    for g in found:
        _front, body = glosses.split_front_matter(g.pop("file").read_text(encoding="utf-8"))
        if not glosses.opens_with_math(body):
            first = next((line.strip() for line in body.splitlines() if line.strip()), "")
            bad.append({**g, "opens": first[:120]})
    return {
        "target": target_id,
        "glosses_schema": doc.get("schema"),
        "rendered_from": doc.get("rendered_from"),
        "current": len(found),
        "not_math_first": bad,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--graph", type=Path, required=True, help="a checkout of the graph")
    ap.add_argument("--target", required=True, help="the target id")
    args = ap.parse_args(argv)
    try:
        report = check(args.graph, args.target)
    except (OSError, ValueError, KeyError) as exc:
        print(
            f"cannot read targets/{args.target}/glosses.json or a version it names: {exc}",
            file=sys.stderr,
        )
        return 2
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 1 if report["not_math_first"] else 0


if __name__ == "__main__":
    sys.exit(main())
