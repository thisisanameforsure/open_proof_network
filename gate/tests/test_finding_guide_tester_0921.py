"""F10-T12: the guide says what the gate and the service do (testers 2026-09-21, items 6 and 9).

Three outside agents read the guide closely and quoted it back where the network contradicted
it. The worst: one paragraph says a skeleton's parent may be proved directly at any time, and a
later one that "any proof of the parent, even one that uses no hole, fails step 4 with
``dep-unproved``". The first is the gate's rule (R22: an unproved hole is not staged and blocks
nothing), so the second cost agents a choice they were free to make. The behaviour is pinned
here beside the words, so the two cannot drift apart again.

Each sentence test was red before the guide was edited.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from harness import make_context, node_dir
from test_finding_hole_frontier import write_hole

from opn_gate import layout, pipeline, postmerge

ROOT = Path(__file__).resolve().parents[2]
GUIDE = (ROOT / "gate" / "agents" / "AGENTS.md").read_text(encoding="utf-8")
FLAT = re.sub(r"\s+", " ", GUIDE)

GONE = {
    "a direct proof is refused until the holes are proved": "even one that uses no hole, fails",
    "the witness slot always says True": "says `theorem witness : True := by sorry` whatever",
    "the fast check answers in about a second": "comes back in about a second",
}

PRESENT = {
    "a direct proof of a parent is accepted whatever its holes": "A direct proof of the parent",
    "the one import a proof may add": "the one import a proof may add",
    "the closing block on get_node": "`closing`",
    "witness mode": '"mode": "witness"',
    "the expected witness type binds every binder": "binders that come after a hypothesis",
    "the fast check's budget and its refusal": "`504 check-timeout`",
    "a cited annex that is still open": "`409 annex-pending`",
    "a cited annex nobody submitted": "`400 annex-unknown`",
    "the merge queue": "holds the queue",
    "one gate round is not the time to merge": "one gate round",
    "gate-written holes and step 6": "recorded and not refused",
    "Lean in an annex goes in a fence": "inside a fenced code block",
    "the MCP's two result shapes": "`{status, body}`",
    "the node-superseded warning": "`node-superseded`",
    "where waiting_on lives": "carries no `waiting_on`",
}


@pytest.mark.parametrize("what", sorted(GONE))
def test_a_sentence_the_network_contradicts_is_gone(what: str) -> None:
    assert GONE[what] not in FLAT, what


@pytest.mark.parametrize("what", sorted(PRESENT))
def test_the_guide_says(what: str) -> None:
    assert PRESENT[what] in FLAT, what


def test_the_mcp_address_is_near_the_top() -> None:
    """The erdos-402 agent, told to prefer the MCP, read the whole HTTP walkthrough before finding
    its address on the last line of a 54,000-character page."""
    assert "/mcp" in GUIDE[: GUIDE.index("## The tutorial node")]


def test_a_parent_with_an_unproved_hole_takes_a_direct_proof(tmp_path: Path) -> None:
    """Item 6, pinned as behaviour: what the guide now says is what step 4's staging does."""
    parent = "and-reassoc"
    ctx = make_context(tmp_path, node_id=parent)
    nodes = layout.graph_nodes_dir(ctx.graph_root, ctx.claim.target_id)
    write_hole(
        ctx.graph_root, witness="theorem witness : True := trivial\n", node_id=f"{parent}--h1"
    )
    meta = node_dir(ctx) / "META.yaml"
    meta.write_text(
        meta.read_text("utf-8").replace("deps: []", f"deps: [{parent}--h1]"), encoding="utf-8"
    )
    postmerge.regenerate_context(node_dir(ctx), nodes)  # as the post-merge job leaves the parent
    assert not (nodes / f"{parent}--h1" / "Proof.lean").exists(), "guard: the hole is unproved"
    verdict = pipeline.run_steps(ctx)
    assert verdict.ok, verdict.diagnostic
