"""F08-T18: a defect claim knows the node's state (testers 2026-09-24; ruling D2).

Six agents on the calibration targets, 2026-09-24. Graph #187 and #194 were circularity claims on
nodes that already carried one: #194 was filed while #187 was open, and a third agent filed on a
node whose circularity claim had merged hours before and whose ``graph.json`` row already read
``cause: circular``. ``POST /defect-claims`` answered 201 each time: ``resolve_ref`` reads the
node's facts from the products and throws them away, and the only duplicate rule on the route is
``duplicates.check_append``'s byte-identical text, which two agents' claims never are (each carries
its own contributor, date and exhibit). By D-25 these are not copies, so the owner ruled on them
as defects (D2, 2026-09-24): a defect claim of the same class is **refused** when one has merged,
and **named in the receipt** when one is open.

The products record one class's merge, and only one: a merged ``circular-decomposition`` claim puts
``cause: circular`` on the node (F08-T17). So:

* a circularity claim on a node whose cause is ``circular`` answers ``409 node-circular`` in
  ``claims.circular()``'s words, naming the merged claim's path, and opens nothing;
* while a claim of the same class is open on the node, the 201 body carries
  ``also_open: [{pr_number, pseudonym}]``; the key is absent when nothing of that class is open;
* a different class on a circular node is still accepted (a circular node may have other defects);
* a claim on another node sees neither.

Red run: ``engineering/evidence/F08/task-18.txt``.
"""

from __future__ import annotations

import pytest
import yaml
from api_fakes import TUTORIAL_NODE, Harness
from test_claims_defect import commit_statement, post
from test_finding_circular_claim import (
    ANCESTOR,
    HOLE,
    TARGET,
    VALID,
    add_ancestor,
    commit_graph,
    graph_rows,
)

RED = "F08-T18: POST /defect-claims ignores the node's cause and its open claims"
MERGED_CLAIM = f"targets/{TARGET}/nodes/{HOLE}/defects/20260924T090000Z-carol.yaml"
OTHER_EXHIBIT = (
    "theorem circular' :\n"
    "    (∀ p q r : Prop, (p ∧ q) ∧ r → r ∧ (q ∧ p)) →\n"
    "    ∀ p q r : Prop, (p ∧ q) ∧ r → p ∧ (q ∧ r) := by\n"
    "  intro _ p q r h\n"
    "  exact ⟨h.1.1, h.1.2, h.2⟩\n"
)


def make_circular(h: Harness) -> None:
    add_ancestor(h)
    mark_circular(h)


def mark_circular(h: Harness) -> None:
    """The state a merged circularity claim leaves: the claim file on ``main`` and the node's
    ``graph.json`` row reading ``cause: circular`` (status untouched, F08-T17)."""
    rows = [{**r, "cause": "circular"} if r["node_id"] == HOLE else r for r in graph_rows(h)]
    commit_graph(h, rows)
    merged = {
        "schema": "defect-claim/v3",
        "stmt_ref": HOLE,
        "class": "circular-decomposition",
        "ancestor": ANCESTOR,
        "line": 1,
        "exhibit": VALID["exhibit"],
        "contributor": "carol",
        "date": "2026-09-24",
    }
    h.githost.files[MERGED_CLAIM] = yaml.safe_dump(merged, sort_keys=True).encode()


@pytest.mark.xfail(strict=True, reason=RED)
def test_a_circularity_claim_on_a_circular_node_is_refused_with_the_merged_claims_path(
    harness: Harness,
) -> None:
    make_circular(harness)
    token = harness.token_for("code_alice", "alice")
    r = post(harness, "/defect-claims", token, VALID)
    body = r.json()
    assert (r.status_code, body.get("error")) == (409, "node-circular"), body
    assert "circular" in body["message"] and "D-16" in body["message"], body["message"]
    assert MERGED_CLAIM in body["message"], body["message"]
    assert body["details"]["cause"] == "circular"
    assert harness.githost.pushes == [], "a refused claim opens nothing"


@pytest.mark.xfail(strict=True, reason=RED)
def test_an_open_same_class_claim_is_named_in_the_receipt(harness: Harness) -> None:
    """#187 then #194: the second is accepted and told the first is open."""
    add_ancestor(harness)
    alice = harness.token_for("code_alice", "alice")
    bob = harness.token_for("code_bob", "bob")
    first = post(harness, "/defect-claims", alice, VALID)
    assert first.status_code == 201, first.text
    assert "also_open" not in first.json(), "nothing was open before the first"
    second = post(harness, "/defect-claims", bob, {**VALID, "exhibit": OTHER_EXHIBIT})
    assert second.status_code == 201, second.text
    assert second.json().get("also_open") == [
        {"pr_number": first.json()["pr_number"], "pseudonym": "alice"}
    ], second.json()


def test_an_open_claim_of_another_class_is_not_named(harness: Harness) -> None:
    add_ancestor(harness)
    alice = harness.token_for("code_alice", "alice")
    bob = harness.token_for("code_bob", "bob")
    junk = {k: v for k, v in VALID.items() if k != "ancestor"} | {"class": "junk-value"}
    assert post(harness, "/defect-claims", alice, junk).status_code == 201
    second = post(harness, "/defect-claims", bob, VALID)
    assert second.status_code == 201, second.text
    assert "also_open" not in second.json(), second.json()


def test_a_different_class_on_a_circular_node_is_still_accepted(harness: Harness) -> None:
    make_circular(harness)
    token = harness.token_for("code_alice", "alice")
    body = {k: v for k, v in VALID.items() if k != "ancestor"} | {"class": "vacuity"}
    r = post(harness, "/defect-claims", token, body)
    assert r.status_code == 201, r.text
    assert "also_open" not in r.json()


def test_a_claim_on_another_node_sees_nothing(harness: Harness) -> None:
    """A circularity claim open on the hole says nothing to one on its sibling, and the hole's
    merged claim refuses nothing there."""
    add_ancestor(harness)
    commit_statement(harness)
    alice = harness.token_for("code_alice", "alice")
    bob = harness.token_for("code_bob", "bob")
    assert post(harness, "/defect-claims", alice, VALID).status_code == 201
    mark_circular(harness)
    sibling = post(harness, "/defect-claims", bob, {**VALID, "stmt_ref": TUTORIAL_NODE})
    assert sibling.status_code == 201, sibling.text
    assert "also_open" not in sibling.json(), sibling.json()
