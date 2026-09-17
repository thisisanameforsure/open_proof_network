"""Finding: a hole blocked only by its unfilled witness slot never reached the frontier.

Found live 2026-09-16. An agent testing the network submitted a partial on ``erdos-412``; the
post-merge job created the hole ``erdos-412--h1`` (``origin: skeleton-hole``, a stub
``Witness.lean``, ``cause: witness-missing``) and derived the root ``blocked`` on it. The target
then vanished from the frontier entirely — 23 entries to 22 — so the next agent reading
``list_frontier`` saw no way to work that conjecture, while ``targets/index.json`` went on saying
the target was ``claimable: true`` with no reasons against it.

That is a defect against D-29, not a design choice. The decisions document says it four times —
"partial holes enter the frontier as compiler-derived children on gate pass", "Residual holes
enter the frontier directly ... no human promotion step", "k holes enter the frontier as
compiler-derived children (D-29); root stays open; its holes are new attack-route nodes" — and
D-25 publishes ``origin: skeleton-hole`` as a frontier field to *filter on*, which is dead weight
if no hole is ever an entry. ``FRONTIER_STATUSES`` is ``("ready", "speculative")``, so every hole,
being ``blocked``, was excluded.

The witness *is* the work: ``POST /proposals/witness`` accepts exactly a hole whose cause is
``witness-missing`` (``hole_awaiting_witness``), and refuses a witness carrying a ``sorry``. So
such a hole is both listable and claimable — the owner's call, 2026-09-16. A node blocked on an
unproved dependency stays off the frontier, because nothing about it can be worked yet; that is
the distinction ``blocked_because`` already draws and this fix reuses rather than re-derives.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import samples
import yaml
from harness import TARGET, copy_graph

from opn_gate import graph, layout, products, schemas

ROOT_NODE = "and-swap-reassoc"
HOLE = "and-swap-reassoc--h1"
AUTHOR = "thisisanameforsure"
DATE = "2026-09-16"
COMMIT_TIME = "2026-09-16T12:00:00Z"

#: The slot the post-merge job writes: a `sorry` as a token in code, so ``witness_is_stub`` is
#: true of it. ``mentions_sorry`` strips comments first, so the header alone would not count.
STUB_WITNESS = (
    "/-! The witness slot for a hole (D-29, F07-R6). Replace `sorry` with an instance\n"
    "satisfying this statement's hypotheses; until then the node is blocked. -/\n\n"
    "theorem witness : True := by\n  sorry\n"
)
REAL_WITNESS = "/-! A filled slot. -/\n\ntheorem witness : True := trivial\n"


def status_of(tg: graph.TargetGraph):  # type: ignore[no-untyped-def]
    return lambda node_id: tg.statuses.get(node_id, "ready")


def hole_of(tg: graph.TargetGraph, **kw: Any) -> graph.NodeFacts:
    """A hole as the post-merge job makes one: a skeleton-hole origin with a stub witness."""
    fields: dict[str, Any] = {
        "origin": "skeleton-hole",
        "witness_stub": True,
        "deps": (),
        "relation": None,
    }
    fields.update(kw)
    return replace(tg.nodes[ROOT_NODE], **fields)


def test_the_stub_witness_is_what_blocks_it(tmp_path: Path) -> None:
    """The premise: such a node is blocked, and the cause is mechanical and nameable."""
    root = copy_graph(tmp_path, publish=True)
    tg = graph.load_target(root, TARGET)
    hole = hole_of(tg)
    blocked, cause = graph.blocked_because(hole, status_of(tg))
    assert (blocked, cause) == (True, graph.CAUSE_WITNESS_MISSING)
    # And the same node with its slot filled is not blocked at all.
    filled = replace(hole, witness_stub=False)
    assert graph.blocked_because(filled, status_of(tg)) == (False, None)


def test_a_witness_missing_hole_is_on_the_frontier(tmp_path: Path) -> None:
    """D-29: holes enter the frontier as children, with no human promotion step."""
    root = copy_graph(tmp_path, publish=True)
    tg = graph.load_target(root, TARGET)
    hole = hole_of(tg)
    assert products.in_frontier("blocked", hole, status_of(tg)), (
        "a hole whose only blocker is its unfilled witness slot is the frontier's business (D-29)"
    )


def test_a_hole_blocked_on_an_unproved_dependency_is_not(tmp_path: Path) -> None:
    """The distinction that keeps this narrow: a dependency nobody has proved is not work the
    reader of the frontier can take, so such a node stays off it."""
    root = copy_graph(tmp_path, publish=True)
    tg = graph.load_target(root, TARGET)
    waiting = hole_of(tg, deps=(ROOT_NODE,))
    assert tg.statuses[ROOT_NODE] != "proved", "the fixture's root is unproved, as this needs"
    assert not products.in_frontier("blocked", waiting, status_of(tg))


def test_a_witness_missing_hole_is_claimable(tmp_path: Path) -> None:
    """Owner's call 2026-09-16: the witness is the work and ``propose_witness`` takes it, so a
    claim on such a hole can be worked — unlike a claim on a node waiting for a dependency."""
    root = copy_graph(tmp_path, publish=True)
    tg = graph.load_target(root, TARGET)
    hole = hole_of(tg)
    blocked_tg = replace(tg, statuses={**tg.statuses, ROOT_NODE: "blocked"})

    def entry(node: graph.NodeFacts, *, target_claimable: bool = True) -> dict[str, Any]:
        return products.frontier_entry(
            blocked_tg,
            node,
            claimable=target_claimable,
            dormant=False,
            ready_since=None,
            tags=[],
        )

    assert entry(hole)["claimable"] is True
    # The target's own refusal still governs: an unclaimable target keeps its holes unclaimable.
    assert entry(hole, target_claimable=False)["claimable"] is False
    # And a node blocked on a dependency is listed-or-not by R5, never claimable.
    assert entry(hole_of(tg, deps=(ROOT_NODE,)))["claimable"] is False


def test_the_variant_rule_is_untouched(tmp_path: Path) -> None:
    """F03-T6 stands: an open variant stays listed while it waits on its holes, and a claim on it
    is still refused, because there the premise "it could not be worked" is true."""
    root = copy_graph(tmp_path, publish=True)
    tg = graph.load_target(root, TARGET)
    variant = replace(tg.nodes[ROOT_NODE], origin="variant")
    assert products.in_frontier("blocked", variant, status_of(tg))
    entry = products.frontier_entry(
        replace(tg, statuses={**tg.statuses, ROOT_NODE: "blocked"}),
        variant,
        claimable=True,
        dormant=False,
        ready_since=None,
        tags=[],
    )
    assert entry["claimable"] is False


def declare_root(root: Path) -> None:
    """A hole nothing depends on is a second sink, so the root is declared (F08-Q19, F11-R14) —
    every fixture that grows a sink must, or root inference refuses the target."""
    doc = samples.target_status(
        root=ROOT_NODE,
        author=AUTHOR,
        date=DATE,
        cause="the root, declared beside a hole nothing depends on yet (F08-Q19)",
    )
    assert schemas.violations(doc, "target-status/v2") == []
    status = root / "targets" / TARGET / "status"
    status.mkdir(exist_ok=True)
    (status / f"{DATE}-{AUTHOR}.yaml").write_text(
        yaml.safe_dump(doc, sort_keys=False), encoding="utf-8"
    )


def write_hole(
    root: Path, *, witness: str, node_id: str = HOLE, supersedes: str | None = None
) -> None:
    """A hole on disk as the post-merge job writes one, so the product is generated from a tree
    rather than from a ``replace``d dataclass (the fixture's passes are worth less than the live
    shape otherwise). With ``supersedes`` it is the hole's D-8 revision instead (``meta/v4``),
    as ``curator.revise`` scaffolds one (F03-T10)."""
    node_dir = root / "targets" / TARGET / "nodes" / node_id
    node_dir.mkdir(parents=True)
    statement = (
        "/-! Hole of a merged partial proof, as a node (D-12 #5, D-29). -/\n\n"
        f"theorem {node_id.replace('-', '_')} : True := by\n  sorry\n"
    )
    (node_dir / "Statement.lean").write_text(statement, encoding="utf-8")
    (node_dir / "Witness.lean").write_text(witness, encoding="utf-8")
    (node_dir / "Context.lean").write_text("", encoding="utf-8")
    # The layout a node directory must have; the post-merge job creates all three (the live
    # ``erdos-412--h1`` carries them), and ``layout.load_node`` refuses the node without them.
    for name in ("attempts", "annex", "explainer"):
        (node_dir / name).mkdir()
        (node_dir / name / layout.KEEP_FILE).write_text("", encoding="utf-8")
    fields: dict[str, Any] = {
        "schema": "meta/v3",
        "id": node_id,
        "status": "blocked",
        "deps": [],
        "origin": "skeleton-hole",
        "tutorial": False,
        "statement-hash": schemas.content_hash(statement.encode()),
    }
    if supersedes is not None:
        fields.update(schema="meta/v4", supersedes=supersedes)
    doc = samples.meta(**fields)
    (node_dir / "META.yaml").write_text(yaml.safe_dump(doc, sort_keys=True), encoding="utf-8")
    declare_root(root)


def test_the_generated_frontier_carries_the_hole(tmp_path: Path) -> None:
    """End to end over a tree: the product the gate renders lists the hole and marks it
    claimable, which is what ``list_frontier`` and the site read."""
    root = copy_graph(tmp_path, publish=True)
    write_hole(root, witness=STUB_WITNESS)
    tg = graph.load_target(root, TARGET)
    assert tg.statuses[HOLE] == "blocked"
    assert graph.derive_causes(tg.nodes, tg.statuses)[HOLE] == graph.CAUSE_WITNESS_MISSING

    built = products.generate(root, rendered_from=None, commit_time=COMMIT_TIME)
    doc = json.loads(built.files[Path("frontier.json")].decode("utf-8"))
    entries = {e["node_id"]: e for e in doc["entries"]}
    assert HOLE in entries, f"the hole is not on the frontier: {sorted(entries)}"
    assert entries[HOLE]["origin"] == "skeleton-hole"
    assert entries[HOLE]["claimable"] is True
    schemas.validate(doc, products.FRONTIER_SCHEMA)


def test_a_filled_slot_leaves_the_hole_ready(tmp_path: Path) -> None:
    """The other end of the same story: once the witness lands the hole is an ordinary ready
    node, and nothing here is what keeps it on the frontier."""
    root = copy_graph(tmp_path, publish=True)
    write_hole(root, witness=REAL_WITNESS)
    tg = graph.load_target(root, TARGET)
    assert tg.statuses[HOLE] == "ready"
    assert products.in_frontier("ready", tg.nodes[HOLE], status_of(tg))
