"""F04-T48: one tree carrying everything a statement panel can show, for the panel redesign.

The fixture graph's root (proved) split by one merged partial into two holes; the partial follows
a stepped annex (a plan) whose steps name the holes; a note on the root that opens with bold;
an approach record on the target; on the first hole a math-first statement gloss with convention
notes and a proposed literature status; the second hole with no gloss. The products are the
gate's own (``products.generate``), lifted to the v3.35 contract for the literature field.
"""

from __future__ import annotations

from pathlib import Path

import fixture
import gloss_fixture as gf
import yaml
from harness import TARGET, copy_graph
from test_decompositions import HOLE_IDS, add_hole, merged_partial
from test_outline_links import stepped
from test_products import ROOT_NODE, nodes_dir

from opn_gate import products
from opn_site import model, render

REPO = "https://github.com/example/graph"
ROOT = ROOT_NODE
H1, H2 = HOLE_IDS
PLAN = "c" * 64
NOTE = "d" * 64
PARTIAL_NAME = "20260920T000000Z-alice-partial.lean"
#: The hole's gloss: its statement in display math, then the conventions (F20-T16's contract).
MATH_GLOSS = (
    "$$p \\land q \\to q \\land p$$\n\n"
    "- Lean writes the swap with `And.symm`.\n"
    "- Both propositions are arbitrary.\n"
)
PLAN_TEXT = (
    "Split the claim at the conjunction: first $p$, then $q$. "
    "Each half is then a hole of its own.\n\nThe rest of the plan is longer.\n"
)
NOTE_TEXT = (
    "**Numerical check, 2026-10-12.** The hypotheses were tested over a finite range. This is "
    "not a proof.\n\n- Range searched: everything small.\n"
)
APPROACH = "20261009T125043Z-t1009-b.yaml"
APPROACH_RECORD = {
    "schema": "approach-record/v1",
    "target": TARGET,
    "contributor": "t1009-b",
    "route": "Close the first hole by a direct sieve.",
    "outcome": "blocked",
    "blocked_on": "an explicit bound not in Mathlib",
    "pinned_mathlib_sha": None,
    "model_and_tooling": "a model",
    "date": "2026-10-09T12:50:42Z",
}
LITERATURE_SUMMARY = "No proof is known; the summary is the contributor's reading."


def summary_tree(tmp_path: Path) -> Path:
    root = copy_graph(tmp_path, publish=True)
    add_hole(root, H1, "hden")
    add_hole(root, H2, "hrem")
    merged_partial(root, 7, ["hden", "hrem"], path=f"attempts/{PARTIAL_NAME}", annex=PLAN)
    annexes = nodes_dir(root) / ROOT / "annex"
    (annexes / f"{PLAN}.md").write_text(stepped(PLAN_TEXT, "hden", "hrem"), encoding="utf-8")
    (annexes / f"{NOTE}.md").write_text(NOTE_TEXT, encoding="utf-8")
    gf.gloss(root, MATH_GLOSS, kind="statement", node=H1, author="alice")
    approaches = root / "targets" / TARGET / "approaches"
    approaches.mkdir(exist_ok=True)
    (approaches / APPROACH).write_text(yaml.safe_dump(APPROACH_RECORD), encoding="utf-8")
    return root


def publish(root: Path) -> None:
    """The products, then the literature status on the first hole as the v3.35 gate writes it."""
    products.generate(root, rendered_from=fixture.COMMIT, commit_time=fixture.NOW).write(root)
    record = fixture.write_literature(
        root,
        H1,
        status="open",
        contributor="t1009-b",
        date="2026-10-09T12:51:37Z",
        references=[
            {
                "title": "E. F. Ecklund, 1969",
                "url": "https://www.erdosproblems.com/1094",
                "note": None,
            }
        ],
        summary=LITERATURE_SUMMARY,
    )
    fixture.publish_v335(
        root,
        literature_proposed={H1: {"status": "open", "record": record, "contributor": "t1009-b"}},
    )


def pages(root: Path) -> dict[str, str]:
    publish(root)
    return render.render_site(model.load_site(root, fixture.COMMIT), repo_url=REPO)


def problem_page(files: dict[str, str]) -> str:
    return files[f"problems/{TARGET}/index.html"]


def node_page(files: dict[str, str], node_id: str) -> str:
    return files[f"nodes/{TARGET}/{node_id}/index.html"]
