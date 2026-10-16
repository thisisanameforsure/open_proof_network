"""F04-T53: render the fixture tree carrying a merged circularity claim, with the gate and site
of whichever checkout this is run against, into a directory a browser can serve.

The tree is the site fixture's revised-hole graph with one ``circular-decomposition`` claim on
``and-swap-reassoc--h1`` naming the root as its ancestor (the claim ``test_finding_circularity_
retired_site`` files). Products come from that checkout's own gate; where its fixture still has
the v3.35 label helper (``publish_v335(circular=...)``, i.e. before F08-T42) the hole's row is
given the label the old gate published, so "before" shows what the live site showed.

    uv run --frozen python engineering/evidence/F04/task-53-render.py --repo <checkout> --out <dir>
"""

from __future__ import annotations

import argparse
import inspect
import sys
import tempfile
from pathlib import Path

import yaml


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()
    repo = args.repo.resolve()
    sys.path[:0] = [
        str(repo / "site" / "tests"),
        str(repo / "gate" / "tests"),
        str(repo / "site"),
        str(repo / "gate"),
    ]
    import fixture  # noqa: PLC0415
    from harness import TARGET  # noqa: PLC0415

    from opn_gate import products  # noqa: PLC0415
    from opn_site import model, render  # noqa: PLC0415

    hole, ancestor = fixture.HOLE, "and-swap-reassoc"
    claim_ref = f"{hole}/defects/20260923T120000Z-alice.yaml"
    with tempfile.TemporaryDirectory() as tmp:
        root = fixture.build_with_revised_hole(Path(tmp))
        path = root / "targets" / TARGET / "nodes" / claim_ref
        path.parent.mkdir(parents=True)
        doc = {
            "schema": "defect-claim/v3",
            "stmt_ref": hole,
            "class": "circular-decomposition",
            "ancestor": ancestor,
            "line": 1,
            "exhibit": "theorem circular : True → True := id\n",
            "contributor": "alice",
            "date": "2026-09-23",
        }
        path.write_text(yaml.safe_dump(doc, sort_keys=True), encoding="utf-8")
        products.generate(root, rendered_from=fixture.COMMIT, commit_time=fixture.NOW).write(root)
        if "circular" in inspect.signature(fixture.publish_v335).parameters:
            fixture.publish_v335(
                root, circular={hole: [{"ancestor": ancestor, "claim": claim_ref}]}
            )
            mode = "before: graph/v9 with the label on the hole's row"
        else:
            mode = f"after: {products.GRAPH_SCHEMA}, no label"
        files = render.render_site(
            model.load_site(root, fixture.COMMIT), repo_url="https://github.com/example/graph"
        )
    for rel, body in files.items():
        target = args.out / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(body, bytes):
            target.write_bytes(body)
        else:
            target.write_text(body, encoding="utf-8")
    print(f"{mode}; {len(files)} files -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
