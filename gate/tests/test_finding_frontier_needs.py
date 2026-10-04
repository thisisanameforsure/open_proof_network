"""F03-T16 (audit 2026-10-04): a frontier entry says what its node needs.

``frontier/v3`` entries carried no status, no cause and no next action, so a reader of
``frontier.json`` (``list_frontier``) could not tell a hole that waits for a witness from a node
that waits for a proof. Live, three holes waiting only for their witness (``blocked``, cause
``witness-missing``) were published ``claimable: true``; an agent that claimed one was then told
``409 node-blocked`` by every write that followed, because the work on such a node goes through
``POST /proposals/witness`` and no claim reserves it. ``frontier/v4`` adds per entry:

- ``status``: the node's derived status (``graph.derive_statuses``), as ``graph.json`` has it;
- ``cause``: the derived cause (``graph.derive_causes``), ``null`` where there is none;
- ``needs``: what would move the node, derived from the same two facts the membership rule reads
  (``products.in_frontier``): ``proof`` (ready or speculative), ``witness`` (a hole blocked only
  by its unfilled slot), ``dependencies`` (an open variant waiting on unproved dependencies), or
  ``null`` when no contributor's submission moves it (a variant under a refuted dependency, or a
  curator's ``stale``/``disputed`` record).

``claimable`` is now true only where ``needs`` is ``proof``: the hole stays on the frontier
(D-29, F03-Q11) and says it needs a witness, and is no longer published as claimable.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

from harness import TARGET, copy_graph
from test_finding_hole_frontier import COMMIT_TIME, HOLE, ROOT_NODE, STUB_WITNESS, write_hole

from opn_gate import graph, products, schemas


def frontier_of(root: Path) -> dict[str, Any]:
    built = products.generate(root, rendered_from=None, commit_time=COMMIT_TIME)
    doc: dict[str, Any] = json.loads(built.files[Path("frontier.json")].decode("utf-8"))
    return doc


def test_a_witness_missing_hole_needs_a_witness_and_is_not_claimable(tmp_path: Path) -> None:
    """The live defect: the hole reads ``claimable: true`` with nothing saying it is blocked."""
    root = copy_graph(tmp_path, publish=True)
    write_hole(root, witness=STUB_WITNESS)
    doc = frontier_of(root)
    entries = {e["node_id"]: e for e in doc["entries"]}
    hole = entries[HOLE]
    assert hole["claimable"] is False, "a hole waiting for its witness is published claimable"
    assert (hole["status"], hole["cause"], hole["needs"]) == (
        "blocked",
        graph.CAUSE_WITNESS_MISSING,
        "witness",
    )
    assert doc["schema"] == "frontier/v4" == products.FRONTIER_SCHEMA
    schemas.validate(doc, products.FRONTIER_SCHEMA)


def test_every_entry_says_status_cause_and_needs(tmp_path: Path) -> None:
    """Each entry's status and cause are graph.json's; ``claimable`` implies ``needs: proof``."""
    root = copy_graph(tmp_path, publish=True)
    write_hole(root, witness=STUB_WITNESS)
    doc = frontier_of(root)
    tg = graph.load_target(root, TARGET)
    causes = graph.derive_causes(tg.nodes, tg.statuses)
    assert doc["entries"], "guard: the fixture's frontier is not empty"
    for e in doc["entries"]:
        assert e["status"] == tg.statuses[e["node_id"]], e["node_id"]
        assert e["cause"] == causes[e["node_id"]], e["node_id"]
        if e["claimable"]:
            assert e["needs"] == "proof", e["node_id"]
    ready = [e for e in doc["entries"] if e["status"] == "ready"]
    assert ready, "guard: the fixture has a ready node on the frontier"
    assert all(e["needs"] == "proof" and e["cause"] is None for e in ready)


def entry_for(tg: graph.TargetGraph, node: graph.NodeFacts, status: str) -> dict[str, Any]:
    return products.frontier_entry(
        replace(tg, statuses={**tg.statuses, node.node_id: status}),
        node,
        claimable=True,
        dormant=False,
        ready_since=None,
        tags=[],
    )


def test_an_open_variant_waiting_on_dependencies_needs_them(tmp_path: Path) -> None:
    """R5 lists an open variant whatever it waits on (F03-T6, Q8). Waiting on an unproved
    dependency, its next action is that dependency's proof; under a refuted one, or under a
    curator's record, no submission moves it and ``needs`` is null — the status and cause say why.
    """
    root = copy_graph(tmp_path, publish=True)
    tg = graph.load_target(root, TARGET)
    variant = replace(tg.nodes[ROOT_NODE], origin="variant")
    assert variant.deps, "guard: the fixture's root has dependencies"
    assert any(tg.statuses[d] != "proved" for d in variant.deps), "guard: one is unproved"
    waiting = entry_for(tg, variant, "blocked")
    assert (waiting["status"], waiting["cause"], waiting["needs"], waiting["claimable"]) == (
        "blocked",
        None,
        "dependencies",
        False,
    )
    refuted_dep = variant.deps[0]
    under_refuted = products.frontier_entry(
        replace(tg, statuses={**tg.statuses, ROOT_NODE: "blocked", refuted_dep: "refuted"}),
        variant,
        claimable=True,
        dormant=False,
        ready_since=None,
        tags=[],
    )
    assert (under_refuted["cause"], under_refuted["needs"]) == (graph.CAUSE_DEP_REFUTED, None)
    for record_status in ("stale", "disputed"):
        e = entry_for(tg, variant, record_status)
        assert (e["status"], e["needs"], e["claimable"]) == (record_status, None, False)


def test_ready_and_speculative_need_a_proof(tmp_path: Path) -> None:
    root = copy_graph(tmp_path, publish=True)
    tg = graph.load_target(root, TARGET)
    node = tg.nodes[ROOT_NODE]
    for status in ("ready", "speculative"):
        e = entry_for(tg, replace(node, deps=()), status)
        assert (e["status"], e["cause"], e["needs"], e["claimable"]) == (
            status,
            None,
            "proof",
            True,
        )
