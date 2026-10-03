"""F18-T4 (R4; AC6, AC7): each merged partial, the annex it followed, and the holes it made.

The skeleton names its annex in the file (D-31 v3.12), the partial's attestation names the file
(step 2) and its holes (step 4), and the post-merge job writes each hole's name into its child's
header. Nothing kept the three together, so no product could say which outline a decomposition
followed or which child is which hole. ``graph.json``'s ``decompositions`` does, read from those
three places and nowhere else.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import samples
import yaml
from harness import TARGET, copy_graph
from test_products import MERGE, ROOT_NODE, nodes_dir, statement_hash

from opn_gate import graph, postmerge, products, schemas

ANNEX = "a" * 64
PARTIAL = "attempts/20260920T000000Z-alice-partial.lean"
HOLE_IDS = (f"{ROOT_NODE}--h1", f"{ROOT_NODE}--h2")


def add_hole(root: Path, child: str, name: str) -> None:
    """A hole child as the post-merge job writes one, recorded as a dep of the root."""
    node = nodes_dir(root) / child
    node.mkdir()
    for sub in ("attempts", "annex", "explainer"):
        (node / sub).mkdir()
    hole = SimpleNamespace(name=name, closed_type="True")
    (node / "Statement.lean").write_text(postmerge.child_statement(child, hole), encoding="utf-8")
    (node / "Context.lean").write_text("/-! no deps -/\n", encoding="utf-8")
    (node / "Witness.lean").write_text("theorem witness : True := trivial\n", encoding="utf-8")
    meta = samples.meta(
        id=child,
        schema="meta/v3",
        origin="skeleton-hole",
        tutorial=False,
        **{"statement-hash": schemas.content_hash((node / "Statement.lean").read_bytes())},
    )
    (node / "META.yaml").write_text(yaml.safe_dump(meta, sort_keys=False), encoding="utf-8")
    parent = nodes_dir(root) / ROOT_NODE / "META.yaml"
    doc = yaml.safe_load(parent.read_text())
    doc["deps"] = [*doc["deps"], child]
    parent.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")


def merged_partial(
    root: Path, n: int, holes: list[str], *, path: str = PARTIAL, annex: str | None = ANNEX
) -> None:
    """A partial's file under ``attempts/`` and its passing attestation, as a merge leaves."""
    file = nodes_dir(root) / ROOT_NODE / path
    file.parent.mkdir(exist_ok=True)
    cite = f"  -- annex: {annex}\n" if annex else ""
    file.write_text(f"theorem x : True := by\n{cite}  sorry\n", encoding="utf-8")
    if annex:
        (nodes_dir(root) / ROOT_NODE / "annex").mkdir(exist_ok=True)
        (nodes_dir(root) / ROOT_NODE / "annex" / f"{annex}.md").write_text("an outline\n")
    steps = [
        {"step": 1, "name": "toolchain", "result": "pass", "diagnostic": None},
        {
            "step": 2,
            "name": "paths",
            "result": "pass",
            "diagnostic": {
                "code": "partial-submission",
                "message": f"a partial proof: {path} (D-12 #5)",
                "details": {"path": path},
            },
        },
        {
            "step": 4,
            "name": "kernel-replay",
            "result": "pass",
            "diagnostic": {
                "code": "artifact-partial",
                "message": "partial",
                "details": {"holes": holes, "kind": "partial"},
            },
        },
    ]
    doc = samples.attestation(
        node_id=ROOT_NODE,
        statement_hash=statement_hash(root, ROOT_NODE),
        merge_commit=MERGE,
        artifact_hash=None,
        steps=steps,
    )
    (root / "attestations").mkdir(exist_ok=True)
    (root / "attestations" / f"{n:06d}.json").write_bytes(schemas.canonical_json(doc))


def decompositions(root: Path) -> list[dict[str, Any]]:
    tg = graph.load_target(root, TARGET)
    doc = schemas.validate(products.graph_doc(tg, None), products.GRAPH_SCHEMA)
    [row] = [n for n in doc["nodes"] if n["node_id"] == ROOT_NODE]
    return list(row["decompositions"])


def test_a_merged_skeleton_names_its_annex_and_its_holes(tmp_path: Path) -> None:
    """AC6."""
    root = copy_graph(tmp_path, publish=True)
    add_hole(root, HOLE_IDS[0], "hden")
    add_hole(root, HOLE_IDS[1], "hrem")
    merged_partial(root, 7, ["hden", "hrem"])
    assert decompositions(root) == [
        {
            "partial": PARTIAL,
            "annex": ANNEX,
            "holes": [{"name": "hden", "node": HOLE_IDS[0]}, {"name": "hrem", "node": HOLE_IDS[1]}],
        }
    ]


def test_a_partial_that_cites_no_annex_says_so(tmp_path: Path) -> None:
    root = copy_graph(tmp_path, publish=True)
    add_hole(root, HOLE_IDS[0], "hT")
    merged_partial(root, 7, ["hT"], annex=None)
    [d] = decompositions(root)
    assert d["annex"] is None and d["holes"] == [{"name": "hT", "node": HOLE_IDS[0]}]


def test_two_partials_are_listed_in_the_record_order_each_with_its_own_holes(
    tmp_path: Path,
) -> None:
    root = copy_graph(tmp_path, publish=True)
    add_hole(root, HOLE_IDS[0], "hT")
    add_hole(root, HOLE_IDS[1], "integrality")
    later = "attempts/20260924T000000Z-bob-partial.lean"
    merged_partial(root, 9, ["integrality"], path=later, annex="b" * 64)
    merged_partial(root, 7, ["hT"])
    assert [(d["partial"], d["annex"], d["holes"]) for d in decompositions(root)] == [
        (PARTIAL, ANNEX, [{"name": "hT", "node": HOLE_IDS[0]}]),
        (later, "b" * 64, [{"name": "integrality", "node": HOLE_IDS[1]}]),
    ]


def test_a_partial_file_with_no_merged_attestation_is_not_a_decomposition(
    tmp_path: Path,
) -> None:
    """A partial left behind by a postmortem is an attempt, not a decomposition (D-13)."""
    root = copy_graph(tmp_path, publish=True)
    file = nodes_dir(root) / ROOT_NODE / PARTIAL
    file.parent.mkdir(exist_ok=True)
    file.write_text(f"theorem x : True := by\n  -- annex: {ANNEX}\n  sorry\n", encoding="utf-8")
    assert decompositions(root) == []


def test_a_hole_whose_child_cannot_be_found_is_named_with_no_node(tmp_path: Path) -> None:
    """C7: a hole the record names and the tree does not hold is shown as such, not dropped."""
    root = copy_graph(tmp_path, publish=True)
    merged_partial(root, 7, ["ghost"])
    [d] = decompositions(root)
    assert d["holes"] == [{"name": "ghost", "node": None}]


def test_hole_header_round_trips() -> None:
    """AC7: the reader recovers the name the writer wrote, and a D-8 revision's hand-written
    header (erdos-1050--h1-v2, 2026-09-17) reads the same."""
    hole = SimpleNamespace(name="numerator_integral", closed_type="True")
    written = postmerge.child_statement("t--h1", hole, imports=["Mathlib"], opens=["open Nat"])
    assert postmerge.hole_name(written) == "numerator_integral"
    revised = (
        "import Mathlib\n\n"
        "/-! Hole `borwein` of a merged partial proof, as a node (D-12 #5, D-29).\n"
        "Revised statement (D-8): the parent assembly's own `have borwein` type. -/\n\n"
        "theorem t : True := by\n  sorry\n"
    )
    assert postmerge.hole_name(revised) == "borwein"
    assert postmerge.hole_name("theorem t : True := by\n  sorry\n") is None
