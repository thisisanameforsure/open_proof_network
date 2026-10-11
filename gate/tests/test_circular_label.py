"""F08-T39 (with F03-T18, F10-T19; D-12 v3.35, D-16 v3.35): a circularity claim is a label, not a
removal.

The erdos-1094 testers (2026-10-08) showed that the exhibit a ``circular-decomposition`` claim
asks for — *a proof of the hole is a proof of the ancestor* — exists for every one-hole
decomposition and for the last open hole of any decomposition once its siblings are proved: it is
met by every honest reduction (D-12 #4), so taking the hole off the frontier (F08-T17) and the
path with it (F08-T20, v3.22) hid genuine progress and would have hidden the open core of
erdos-1094 behind a proved literature theorem. Whether a route is a loop or a reduction is a
judgment no program makes.

v3.35: the merged claim is published as a fact and removes nothing. ``graph.json`` (``graph/v6``)
carries ``circular: [{ancestor, claim}]`` on every node — the node's own merged claims, and for a
node strictly between a claimed hole and its ancestor on a path whose other holes are proved
(v3.22's rule), the claim that takes it; the frontier (``frontier/v5``) repeats it on every entry,
and a node under a claim is an entry on its status alone; ``CONTEXT.json`` (``context/v5``)
carries it beside ``circular_below``. The node's status, cause, claimability and ``needs`` ignore
the claim, so ``cause`` is never ``circular`` again. Choosing to work on a labelled node is the
operator's filter (D-25); nothing ranks it. Derive, never rewrite: deleting the claim file removes
every label.

``literature`` and ``literature_proposed`` are the other v6/v5/v5 fields; this task writes them as
``null`` and F08-T40 fills them.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from harness import TARGET, copy_graph
from test_finding_circular_decomposition import (
    ANCESTOR,
    CLAIM,
    HOLE,
    file_claim,
    frontier_ids,
    generate,
    graph_row,
)
from test_finding_circular_path import CLAIM as PATH_CLAIM
from test_finding_circular_path import (
    CLAIM_FILE,
    CLAIM_REF,
    DEEP,
    LOW,
    MID,
    PATH,
    ROOT,
    chain,
    claimed,
    prove,
)

from opn_gate import context, graph, products, schemas

OWN_CLAIM = CLAIM.split(f"nodes/{HOLE}/")[1]  # defects/<file>, relative to the hole
HOLE_LABEL = {"ancestor": ANCESTOR, "claim": f"{HOLE}/{OWN_CLAIM}"}
PATH_LABEL = {"ancestor": ROOT, "claim": CLAIM_REF}
NEW_FIELDS = ("circular", "literature", "literature_proposed")


def bundle(prod: products.Products, node_id: str) -> dict[str, Any]:
    return dict(json.loads(prod.files[Path(context.context_path(TARGET, node_id))]))


def entries(prod: products.Products) -> dict[str, dict[str, Any]]:
    doc = json.loads(prod.files[Path("frontier.json")])
    return {str(e["node_id"]): dict(e) for e in doc["entries"]}


# --- the hole stays, labelled -------------------------------------------------------------------


def test_a_claimed_hole_stays_on_the_frontier_claimable_and_labelled(tmp_path: Path) -> None:
    """The behaviour F08-T17 pinned, reversed by D-12 v3.35: the hole is an entry on its status
    alone, its cause is what it would be without the claim, and the claim is a label on it."""
    root = copy_graph(tmp_path, publish=True)
    before = entries(generate(root))[HOLE]
    file_claim(root)
    prod = generate(root)
    assert HOLE in frontier_ids(prod), "the hole stays on the frontier (D-12 v3.35)"
    row = graph_row(prod, HOLE)
    assert row["status"] == "ready"  # nothing about the statement changed (D-3)
    assert row["cause"] is None  # never ``circular`` since graph/v6
    after = entries(prod)[HOLE]
    assert (after["claimable"], after["needs"]) == (before["claimable"], before["needs"])
    assert after["needs"] == "proof"
    assert row["circular"] == [HOLE_LABEL]
    assert after["circular"] == [HOLE_LABEL]
    assert bundle(prod, HOLE)["circular"] == [HOLE_LABEL]


def test_the_products_are_the_next_versions_and_literature_is_null(tmp_path: Path) -> None:
    root = copy_graph(tmp_path, publish=True)
    file_claim(root)
    prod = generate(root)
    gdoc = json.loads(prod.files[Path("targets") / TARGET / "graph.json"])
    fdoc = json.loads(prod.files[Path("frontier.json")])
    cdoc = bundle(prod, HOLE)
    # graph/v7 since F25-T1 (registrations); v6 was F08-T39's.
    assert (gdoc["schema"], fdoc["schema"], cdoc["schema"]) == (
        "graph/v7",
        "frontier/v5",
        "context/v5",
    )
    for doc, schema in ((gdoc, "graph/v7"), (fdoc, "frontier/v5"), (cdoc, "context/v5")):
        assert schemas.violations(doc, schema) == [], schema
    for row in gdoc["nodes"]:
        assert set(NEW_FIELDS) <= set(row), row["node_id"]
        assert row["literature"] is None and row["literature_proposed"] is None
    for entry in fdoc["entries"]:
        assert set(NEW_FIELDS) <= set(entry), entry["node_id"]
        assert entry["literature"] is None and entry["literature_proposed"] is None
    assert cdoc["literature"] is None and cdoc["literature_proposed"] is None
    # A node under no claim carries an empty list, never null.
    assert graph_row(prod, "tutorial-and-swap")["circular"] == []


# --- the path is labelled, the ancestor is not -------------------------------------------------


def test_a_path_node_is_labelled_with_the_claim_that_takes_it(tmp_path: Path) -> None:
    """v3.22's path rule survives as a label: with every sibling on the way proved, each node
    strictly between the claimed hole and its ancestor carries the claim; the ancestor does not."""
    root = chain(tmp_path)
    before = entries(generate(root))
    file_claim(root, PATH_CLAIM, stmt_ref=DEEP, ancestor=ROOT)
    prod = generate(root)
    after = entries(prod)
    assert set(after) == set(before), "no node leaves the frontier for the claim (D-12 v3.35)"
    for node_id in (ROOT, *PATH, DEEP):
        assert after[node_id]["status"] == before[node_id]["status"], node_id
        assert after[node_id]["cause"] == before[node_id]["cause"], node_id
        assert after[node_id]["needs"] == before[node_id]["needs"], node_id
        assert after[node_id]["claimable"] == before[node_id]["claimable"], node_id
    for node_id in PATH:
        assert graph_row(prod, node_id)["circular"] == [PATH_LABEL], node_id
        assert after[node_id]["circular"] == [PATH_LABEL], node_id
    assert graph_row(prod, DEEP)["circular"] == [PATH_LABEL]  # its own claim, named by the hole
    assert graph_row(prod, ROOT)["circular"] == []
    assert after[ROOT]["claimable"] is True


def test_the_four_live_node_shape(tmp_path: Path) -> None:
    """The live record on 2026-10-08: one claim on the deepest hole, every sibling proved, so the
    hole and the two nodes between it and the root are labelled and the root is not — and all
    four are frontier entries, as they were before the claim. The loaded facts say the same."""
    root = claimed(tmp_path)
    tg = graph.load_target(root, TARGET)
    labelled = {n: [c.as_dict() for c in tg.nodes[n].circular] for n in (ROOT, MID, LOW, DEEP)}
    assert labelled == {
        ROOT: [],
        MID: [PATH_LABEL],
        LOW: [PATH_LABEL],
        DEEP: [PATH_LABEL],
    }
    assert tg.nodes[ROOT].circular_below == (CLAIM_REF,)
    on = frontier_ids(generate(root))
    assert {ROOT, MID, LOW, DEEP} <= set(on)
    # The cause is the hole's own mechanical one (its unfilled slot), never ``circular``.
    cause = graph.cause_of(tg.nodes[DEEP], tg.statuses[DEEP], lambda n: tg.statuses[n])
    assert cause == graph.CAUSE_WITNESS_MISSING


def test_a_claim_speaks_along_the_path_only_while_its_hole_is_open(tmp_path: Path) -> None:
    """v3.22 unchanged: once the claimed hole is proved the path label lifts (the route is no
    longer a route to warn about), while the hole's own claim stays a fact on its row."""
    root = claimed(tmp_path)
    prove(root, DEEP, 9)
    prod = generate(root)
    for node_id in PATH:
        assert graph_row(prod, node_id)["circular"] == [], node_id
    assert graph_row(prod, DEEP)["circular"] == [PATH_LABEL]
    assert bundle(prod, ROOT)["circular_below"] == []


def test_a_claim_whose_hole_has_no_proved_sibling_labels_the_hole_alone(tmp_path: Path) -> None:
    root = claimed(tmp_path, unproved=(f"{MID}--h2",))
    prod = generate(root)
    assert graph_row(prod, DEEP)["circular"] == [PATH_LABEL]
    assert all(graph_row(prod, n)["circular"] == [] for n in PATH)
    assert {*PATH, DEEP} <= set(frontier_ids(prod))


# --- CONTEXT.json carries the same label, and the service derives the same bytes -----------------


def test_the_bundle_carries_the_label_beside_circular_below(tmp_path: Path) -> None:
    prod = generate(claimed(tmp_path))
    low = bundle(prod, LOW)
    assert schemas.violations(low, low["schema"]) == []
    assert low["circular"] == [PATH_LABEL] and low["circular_below"] == []
    top = bundle(prod, ROOT)
    assert top["circular"] == [] and top["circular_below"] == [
        {"node_id": DEEP, "claim": PATH_CLAIM}
    ]
    [dep] = [d for d in low["deps"] if d["node_id"] == DEEP]
    # F22-T13's field repeats graph.json's cause, which is the hole's mechanical one (its
    # witness slot) and never ``circular``; the claim is on the dep's own row and bundle.
    assert dep["cause"] == graph_row(prod, DEEP)["cause"] == "witness-missing"


def test_a_bundle_over_an_older_graph_document_derives_the_label(tmp_path: Path) -> None:
    """The deploy window (2026-09-11): the service derives a bundle over the host from the graph
    document the *pinned* gate rendered, which before the re-pin is ``graph/v5`` with no
    ``circular`` field and ``cause: circular`` on the hole. The builder derives the labels from the
    tree then, and the bundle is the one the new gate writes."""
    root = claimed(tmp_path)
    prod = generate(root)
    gdoc = json.loads(prod.files[Path("targets") / TARGET / "graph.json"])
    older = {
        **gdoc,
        "schema": "graph/v5",
        "nodes": [
            {
                **{k: v for k, v in n.items() if k not in NEW_FIELDS},
                "cause": "circular" if n["node_id"] in (*PATH, DEEP) else n["cause"],
            }
            for n in gdoc["nodes"]
        ],
    }
    states = context.graph_states(older)
    assert states[DEEP].circular is None  # the older document does not carry it
    reader = context.DiskReader(root)
    for node_id in (ROOT, MID, LOW, DEEP):
        derived = json.loads(
            context.render(reader, TARGET, node_id, states=states, rendered_from="5" * 40)
        )
        assert derived["circular"] == bundle(prod, node_id)["circular"], node_id
        assert derived["circular_below"] == bundle(prod, node_id)["circular_below"], node_id


# --- derive, never rewrite -----------------------------------------------------------------------


def test_deleting_the_claim_removes_every_label(tmp_path: Path) -> None:
    root = chain(tmp_path)
    before = generate(root).files
    rel = file_claim(root, PATH_CLAIM, stmt_ref=DEEP, ancestor=ROOT)
    prod = generate(root)
    assert prod.files != before
    assert graph_row(prod, LOW)["circular"] == [PATH_LABEL]
    (root / rel).unlink()
    assert generate(root).files == before
    assert CLAIM_FILE in rel
