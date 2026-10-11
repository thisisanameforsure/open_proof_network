"""F22-T14's site half: the reserved ``close`` step, and a case step's new hypotheses.

The gate's outline (F22-T14) now gives a proof's top-level closing tactics a step of their own
with the reserved id ``close``, kind ``term``, outside the ``s<n>`` numbering. Before it, an
outline whose only step was a ``term`` step meant the proof was one term, and the page said
"The proof is a single term". A tactic proof whose only step is ``close`` is not one term, so the
sentence must not appear for it. A ``case`` step's goal now lists the hypotheses its split
introduced; the page shows a step's hypotheses, and still does for a case step.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import fixture
import reading_fixture as rf
import site_outlines as so
from harness import TARGET

from opn_gate import schemas
from opn_site import model, render

REPO = "https://github.com/example/graph"
SINGLE = "The proof is a single term"


def pages_with(tmp_path: Path, steps: list[dict[str, Any]]) -> dict[str, str]:
    root = rf.chain_tree(tmp_path)
    proof = fixture.nodes_dir(root) / rf.ROOT / "Proof.lean"
    digest = schemas.content_hash(proof.read_bytes())
    so.write(root, so.document(rf.ROOT, "Proof.lean", digest, steps))
    rf.write_products(root)
    return render.render_site(model.load_site(root, fixture.COMMIT), repo_url=REPO)


def node_page(pages: dict[str, str]) -> str:
    return pages[f"nodes/{TARGET}/{rf.ROOT}/index.html"]


def test_a_tactic_proof_whose_only_step_is_close_is_not_called_a_single_term(
    tmp_path: Path,
) -> None:
    close = so.step("close", "term", (5, 5), closed_by=("term", []))
    page = node_page(pages_with(tmp_path, [close]))
    assert 'class="po-id">close</code>' in page
    assert SINGLE not in page


def test_a_one_term_proof_still_says_so(tmp_path: Path) -> None:
    term = so.step("s1", "term", (5, 5), closed_by=("term", []))
    assert SINGLE in node_page(pages_with(tmp_path, [term]))


def test_a_case_steps_introduced_hypotheses_are_shown(tmp_path: Path) -> None:
    case = so.step(
        "s1",
        "case",
        (4, 5),
        goal={
            "target": so.text("r ∧ q ∧ p"),
            "hypotheses": [{"name": "hpq_left", "type": so.text("p ∧ q")}],
        },
        closed_by=("steps", []),
    )
    pages = pages_with(tmp_path, [case])
    for page in (node_page(pages), *(v for k, v in pages.items() if "/proofs/" in k)):
        assert "<code>hpq_left : p ∧ q</code>" in page
