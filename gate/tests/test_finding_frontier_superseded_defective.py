"""Finding: the frontier advertised a superseded hole, and a hole whose statement does not
elaborate, as claimable work (F03-T10, R13, AC17; Q12, Q13).

Found live 2026-09-17, in the calibration run's corrections (``engineering/evidence/F15/
calibration.md``, "The last merge proved why the re-pin matters"). A D-8 revision replaced
``erdos-69--h2``; the old node carries a ``superseded`` record naming its successor, and
``frontier.json`` still listed it with ``claimable: true``, because ``products.in_frontier``
admits whatever ``graph.awaiting_witness`` accepts and that asks only whether the witness slot is
a stub and the origin is a hole, never whether the node has been replaced. The sibling whose slot
had been filled correctly dropped off, which is what made the asymmetry legible. And the pinned
extractor wrote ``erdos-69--h2-v2--h1`` with its ascriptions dropped, so its statement does not
typecheck at all; the products rendered, nothing went red, and the node was published as work.

The graph's own ``graph.json`` disagreed with the frontier the whole time: ``derive_causes``
publishes ``cause`` only while ``blocked`` is the status, so the superseded hole had ``cause:
null`` and the api's witness route already refused it. Membership now takes the same reading, and
refuses a superseded node on the fact itself. The only place the products ever elaborate a
statement is the library-tag scan (R6), so a node whose scan raises is learned there and left
out, with the log naming it. What that second rule does not cover is in Q13.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest
import samples
from harness import TARGET, copy_graph
from test_finding_hole_frontier import (
    COMMIT_TIME,
    HOLE,
    ROOT_NODE,
    STUB_WITNESS,
    hole_of,
    status_of,
    write_hole,
)

from opn_gate import curator, graph, layout, products, records, schemas
from opn_gate.graph import GraphError, NodeFacts

SUCCESSOR = HOLE + "-v2"
DATE = "2026-09-17"
INTERIOR = "and-reassoc"
TUTORIAL = "tutorial-and-swap"


def superseded_by(successor: str) -> records.StatusRecord:
    """The record ``curator.revise`` writes on the old node, as a dataclass."""
    doc = {"status": "superseded", "reference": successor}
    return records.StatusRecord("superseded", "curator", DATE, Path("x"), doc)


def record_of(status: str) -> records.StatusRecord:
    return records.StatusRecord(status, "curator", DATE, Path("x"), {"status": status})


def supersede(root: Path, node_id: str, successor: str) -> None:
    """The record on disk, through the curator's own writer."""
    node = layout.graph_nodes_dir(root, TARGET) / node_id
    doc = curator.node_status_doc(
        "superseded",
        f"superseded by {successor} (D-8)",
        author="curator",
        date=DATE,
        reference=successor,
    )
    curator.write_record(node, doc, author="curator", date=DATE)


def pin_mathlib(root: Path) -> None:
    """A Mathlib pin on the fixture, so the products keep a tag cache and run the scan."""
    spec_path = layout.gate_spec_path(root, TARGET)
    spec = schemas.load_json(spec_path)
    spec["mathlib_sha"] = samples.SHA1
    spec_path.write_bytes(schemas.canonical_json(spec))


# --- (a) a superseded node is not work, whatever its slot says ----------------------------------


def test_a_superseded_hole_is_not_on_the_frontier(tmp_path: Path) -> None:
    """The premise, then the rule: the reason alone still says "awaiting its witness", because
    it never looks at the record; membership does, and refuses on the fact."""
    tg = graph.load_target(copy_graph(tmp_path), TARGET)
    superseded = hole_of(tg, override=superseded_by(SUCCESSOR))
    assert graph.awaiting_witness(superseded, status_of(tg))  # the reason cannot tell
    assert not products.in_frontier("superseded", superseded, status_of(tg))
    # The fact wins over a stale status map too.
    assert not products.in_frontier("blocked", superseded, status_of(tg))
    # T9 stands: the same hole with no record is on the frontier for its witness.
    assert products.in_frontier("blocked", hole_of(tg), status_of(tg))


def test_a_superseded_hole_is_not_claimable(tmp_path: Path) -> None:
    tg = graph.load_target(copy_graph(tmp_path), TARGET)
    superseded = hole_of(tg, override=superseded_by(SUCCESSOR))
    entry = products.frontier_entry(
        tg, superseded, claimable=True, dormant=False, ready_since=None, tags=[]
    )
    assert entry["claimable"] is False
    live = products.frontier_entry(
        tg, hole_of(tg), claimable=True, dormant=False, ready_since=None, tags=[]
    )
    assert live["claimable"] is True


@pytest.mark.parametrize("status", ["stale", "disputed", "abandoned"])
def test_a_curator_record_takes_a_hole_off_the_frontier(tmp_path: Path, status: str) -> None:
    """A hole is listed for its unfilled slot only while ``blocked`` is its status: a record that
    changes the status is the curator's word over the mechanical reason, the reading
    ``graph.derive_causes`` already takes for ``cause``."""
    tg = graph.load_target(copy_graph(tmp_path), TARGET)
    recorded = hole_of(tg, override=record_of(status))
    assert not products.in_frontier(status, recorded, status_of(tg))
    # Claimability shares the predicate, and ``frontier_entry`` reads the status from the
    # target's map, which a record fabricated on the dataclass does not change; the end-to-end
    # test below proves it over a tree, where the record is on disk.
    # Speculative is a frontier status in its own right (R5), record or not.
    assert products.in_frontier("speculative", hole_of(tg), status_of(tg))


def test_an_abandoned_variant_is_off_the_frontier_and_the_other_records_are_untouched(
    tmp_path: Path,
) -> None:
    """F03-T13 (Q16, the owner's word 2026-09-20): a variant the curator has marked abandoned
    leaves the frontier as an abandoned ordinary node does (AC4); Q12's clause that kept it
    listed gave way. A stale or disputed variant is still listed, as AC14 says, and a superseded
    variant is not, because its successor carries the question."""
    tg = graph.load_target(copy_graph(tmp_path), TARGET)
    variant = replace(tg.nodes[ROOT_NODE], origin="variant")
    assert not products.in_frontier("abandoned", variant, status_of(tg))
    for kept in ("stale", "disputed", "blocked"):
        assert products.in_frontier(kept, variant, status_of(tg))
    gone = replace(variant, override=superseded_by(ROOT_NODE + "-v2"))
    assert not products.in_frontier("superseded", gone, status_of(tg))


def test_the_generated_frontier_drops_the_superseded_hole_and_keeps_its_successor(
    tmp_path: Path,
) -> None:
    """End to end over a tree, in the live shape: the hole, its revision carrying the same slot
    with ``supersedes``, and the record the curator's writer puts on the old node."""
    root = copy_graph(tmp_path, publish=True)
    write_hole(root, witness=STUB_WITNESS)
    write_hole(root, witness=STUB_WITNESS, node_id=SUCCESSOR, supersedes=HOLE)
    supersede(root, HOLE, SUCCESSOR)

    tg = graph.load_target(root, TARGET)
    assert tg.root == ROOT_NODE
    assert tg.statuses[HOLE] == "superseded" and tg.statuses[SUCCESSOR] == "blocked"
    causes = graph.derive_causes(tg.nodes, tg.statuses)
    # The api's view (``hole_awaiting_witness`` keys off ``cause``): the old hole is refused,
    # the successor is taken. The frontier now says the same.
    assert causes[HOLE] is None and causes[SUCCESSOR] == graph.CAUSE_WITNESS_MISSING

    built = products.generate(root, rendered_from=None, commit_time=COMMIT_TIME)
    doc = json.loads(built.files[Path("frontier.json")].decode("utf-8"))
    entries = {e["node_id"]: e for e in doc["entries"]}
    assert HOLE not in entries, sorted(entries)
    assert SUCCESSOR in entries and entries[SUCCESSOR]["claimable"] is True
    assert entries[SUCCESSOR]["origin"] == "skeleton-hole"
    schemas.validate(doc, products.FRONTIER_SCHEMA)
    # graph.json still carries the old node: it is a fact about the tree, not work to offer.
    gdoc = json.loads(built.files[Path("targets") / TARGET / "graph.json"].decode("utf-8"))
    statuses = {n["node_id"]: n["status"] for n in gdoc["nodes"]}
    assert statuses[HOLE] == "superseded" and statuses[SUCCESSOR] == "blocked"


# --- (b) a statement the pinned toolchain refuses is not work either ----------------------------


def test_a_statement_the_scan_refuses_is_not_on_the_frontier(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """The scan is the one place the products elaborate a statement (R6); when it raises for a
    node, the node is left out, the log names it twice, the other nodes keep their tags, no cache
    entry is written for it, its derived status is untouched, and the next render scans it again
    rather than remembering a failure (Q13)."""
    root = copy_graph(tmp_path, publish=True)
    pin_mathlib(root)
    scanned: list[str] = []

    def scanner(node: NodeFacts) -> list[str]:
        scanned.append(node.node_id)
        if node.node_id == INTERIOR:
            msg = f"opn-used-constants failed on {INTERIOR}: file does not elaborate"
            raise GraphError(msg)
        return ["Order"]

    with caplog.at_level("WARNING", logger="opn_gate.products"):
        built = products.generate(
            root, rendered_from="5" * 40, commit_time=COMMIT_TIME, scanner=scanner
        )
    doc = json.loads(built.files[Path("frontier.json")].decode("utf-8"))
    ids = [e["node_id"] for e in doc["entries"]]
    assert INTERIOR not in ids and TUTORIAL in ids, ids
    tutorial = next(e for e in doc["entries"] if e["node_id"] == TUTORIAL)
    assert tutorial["tags"]["library"] == ["Order"]
    assert INTERIOR in scanned and TUTORIAL in scanned
    cache_rel = Path("targets") / TARGET / products.TAGS_CACHE
    cache = json.loads(built.files[cache_rel].decode("utf-8"))
    tg = graph.load_target(root, TARGET)
    assert tg.nodes[INTERIOR].statement_hash not in cache
    assert tg.nodes[TUTORIAL].statement_hash in cache
    assert f"library tags skipped for {INTERIOR}" in caplog.text
    assert f"{INTERIOR}: its statement does not elaborate" in caplog.text
    gdoc = json.loads(built.files[Path("targets") / TARGET / "graph.json"].decode("utf-8"))
    assert {n["node_id"]: n["status"] for n in gdoc["nodes"]}[INTERIOR] == tg.statuses[INTERIOR]
    schemas.validate(doc, products.FRONTIER_SCHEMA)

    # No negative cache: the next render asks again, and the node is still out.
    built.write(root, write_meta=False)
    scanned.clear()
    second = products.generate(
        root, rendered_from="5" * 40, commit_time=COMMIT_TIME, scanner=scanner
    )
    assert scanned == [INTERIOR]
    again = json.loads(second.files[Path("frontier.json")].decode("utf-8"))
    assert INTERIOR not in [e["node_id"] for e in again["entries"]]
    assert cache_rel not in second.files


def test_a_mathlib_free_graph_never_scans_so_the_rule_cannot_fire(tmp_path: Path) -> None:
    """Q13's first limit, stated: without a Mathlib pin there is no cache and no scan, so the
    frontier is what it always was — the goldens guard that nothing moves."""
    root = copy_graph(tmp_path, publish=True)

    def scanner(node: NodeFacts) -> list[str]:
        raise AssertionError(f"scanned {node.node_id} on a Mathlib-free graph")

    with_scanner = products.generate(
        root, rendered_from=None, commit_time=COMMIT_TIME, scanner=scanner
    )
    without = products.generate(root, rendered_from=None, commit_time=COMMIT_TIME)
    assert with_scanner.files[Path("frontier.json")] == without.files[Path("frontier.json")]
    ids = [e["node_id"] for e in json.loads(without.files[Path("frontier.json")])["entries"]]
    assert INTERIOR in ids
