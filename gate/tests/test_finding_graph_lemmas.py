"""F03-T20 (D-12 v3.36): ``graph/v7`` publishes each node's lemmas.

A hole that restated a node under another branch of the target *is* that node, and the parent
gains it as a lemma — ``META.yaml``'s ``lemmas`` (``meta/v6``, bot-written), read through
``graph.NodeFacts.lemmas``. The product publishes the record (``{hole, node}``, the node as it
is *now*), and a decomposition's hole whose name matches no own-hole child but matches a lemma's
hole resolves to the lemma's node instead of null — which is the live shape of graph #479, where
``erdos-1094--h3``'s one hole restated ``erdos-1094--h2--h1--h1`` and the product said null.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import samples
import yaml
from harness import TARGET, copy_graph
from test_decompositions import PARTIAL, add_hole, merged_partial
from test_products import ROOT_NODE, nodes_dir

from opn_gate import graph, postmerge, products, schemas

#: The branch the lemma lives under: ``and-reassoc`` is a dep of the root, and its hole is a
#: node under another branch than the root's own holes (the live shape).
OTHER_BRANCH = "and-reassoc"
LEMMA = f"{OTHER_BRANCH}--h1"
LEMMA_HOLE = "h_good_below_cube"


def write_node_under(root: Path, child: str, name: str, parent: str) -> None:
    """A hole child as the post-merge job writes one, recorded as a dep of ``parent``."""
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
    parent_meta = nodes_dir(root) / parent / "META.yaml"
    doc = yaml.safe_load(parent_meta.read_text())
    doc["deps"] = [*doc["deps"], child]
    parent_meta.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")


def write_lemmas(root: Path, node_id: str, lemmas: list[dict[str, str]]) -> None:
    """``META.yaml``'s ``lemmas`` as the post-merge job writes them (``meta/v6``)."""
    path = nodes_dir(root) / node_id / "META.yaml"
    doc = yaml.safe_load(path.read_text())
    doc.update(schema="meta/v6", lemmas=lemmas)
    assert schemas.violations(doc, "meta/v6") == [], "the hand-written META is not meta/v6"
    path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")


def revise(root: Path, node_id: str) -> str:
    """A D-8 revision of ``node_id``: the ``-v2`` node that says what it supersedes, and the
    ``superseded`` status record on the original naming it."""
    nodes = nodes_dir(root)
    new = f"{node_id}-v2"
    revised = nodes / new
    revised.mkdir()
    for sub in ("attempts", "annex", "explainer"):
        (revised / sub).mkdir()
    for name in ("Statement.lean", "Context.lean", "Witness.lean"):
        # A statement imports its own Context (F08-T13), so the copy names the new node.
        text = (nodes / node_id / name).read_text(encoding="utf-8")
        (revised / name).write_text(text.replace(f"«{node_id}»", f"«{new}»"), encoding="utf-8")
    meta = yaml.safe_load((nodes / node_id / "META.yaml").read_text())
    meta.update({"id": new, "schema": "meta/v4", "supersedes": node_id})
    meta["statement-hash"] = schemas.content_hash((revised / "Statement.lean").read_bytes())
    (revised / "META.yaml").write_text(yaml.safe_dump(meta, sort_keys=False), encoding="utf-8")
    status = nodes / node_id / "status"
    status.mkdir()
    (status / "2026-10-10-1.yaml").write_text(
        yaml.safe_dump(samples.node_status(status="superseded", reference=new)),
        encoding="utf-8",
    )
    return new


def graph_rows(root: Path) -> dict[str, dict[str, Any]]:
    tg = graph.load_target(root, TARGET)
    doc = products.graph_doc(tg, None)
    assert doc["schema"] == "graph/v7" == products.GRAPH_SCHEMA
    assert schemas.violations(doc, "graph/v7") == [], "graph.json is not graph/v7"
    return {n["node_id"]: n for n in doc["nodes"]}


def with_lemma(tmp_path: Path) -> Path:
    root = copy_graph(tmp_path, publish=True)
    write_node_under(root, LEMMA, LEMMA_HOLE, OTHER_BRANCH)
    write_lemmas(root, ROOT_NODE, [{"hole": LEMMA_HOLE, "node": LEMMA}])
    return root


def test_a_node_with_a_lemma_publishes_it(tmp_path: Path) -> None:
    rows = graph_rows(with_lemma(tmp_path))
    assert rows[ROOT_NODE]["lemmas"] == [{"hole": LEMMA_HOLE, "node": LEMMA}]
    # A lemma is not a dep: the declared list is the record as written (D-3 keeps blocking).
    assert LEMMA not in rows[ROOT_NODE]["deps"]


def test_a_node_without_lemmas_publishes_an_empty_list(tmp_path: Path) -> None:
    rows = graph_rows(copy_graph(tmp_path, publish=True))
    assert all(row["lemmas"] == [] for row in rows.values()), rows


def test_lemmas_keep_the_records_order(tmp_path: Path) -> None:
    root = copy_graph(tmp_path, publish=True)
    write_node_under(root, LEMMA, "hb", OTHER_BRANCH)
    write_node_under(root, f"{OTHER_BRANCH}--h2", "ha", OTHER_BRANCH)
    write_lemmas(
        root,
        ROOT_NODE,
        [{"hole": "hb", "node": LEMMA}, {"hole": "ha", "node": f"{OTHER_BRANCH}--h2"}],
    )
    assert [x["hole"] for x in graph_rows(root)[ROOT_NODE]["lemmas"]] == ["hb", "ha"]


def test_a_decompositions_hole_resolves_to_the_lemma(tmp_path: Path) -> None:
    """Graph #479's shape: the partial's hole matches no own-hole child and one lemma's hole."""
    root = with_lemma(tmp_path)
    add_hole(root, f"{ROOT_NODE}--h1", "h_own")
    merged_partial(root, 7, ["h_own", LEMMA_HOLE])
    [d] = graph_rows(root)[ROOT_NODE]["decompositions"]
    assert d["partial"] == PARTIAL
    assert d["holes"] == [
        {"name": "h_own", "node": f"{ROOT_NODE}--h1"},
        {"name": LEMMA_HOLE, "node": LEMMA},
    ]


def test_an_own_hole_child_wins_over_a_lemma_of_the_same_name(tmp_path: Path) -> None:
    """The record never holds both for one hole, but the rule is the own child first."""
    root = with_lemma(tmp_path)
    add_hole(root, f"{ROOT_NODE}--h1", LEMMA_HOLE)
    merged_partial(root, 7, [LEMMA_HOLE])
    [d] = graph_rows(root)[ROOT_NODE]["decompositions"]
    assert d["holes"] == [{"name": LEMMA_HOLE, "node": f"{ROOT_NODE}--h1"}]


def test_a_hole_the_tree_does_not_hold_is_still_null(tmp_path: Path) -> None:
    root = with_lemma(tmp_path)
    merged_partial(root, 7, ["h_nowhere"])
    [d] = graph_rows(root)[ROOT_NODE]["decompositions"]
    assert d["holes"] == [{"name": "h_nowhere", "node": None}]


def test_a_lemma_pointing_at_a_revised_node_publishes_the_current_id(tmp_path: Path) -> None:
    """D-8: the META still names the superseded node; the product names its revision, in the
    row's ``lemmas`` and in the decomposition that restated it."""
    root = with_lemma(tmp_path)
    new = revise(root, LEMMA)
    merged_partial(root, 7, [LEMMA_HOLE], annex=None)
    rows = graph_rows(root)
    assert rows[ROOT_NODE]["lemmas"] == [{"hole": LEMMA_HOLE, "node": new}]
    [d] = rows[ROOT_NODE]["decompositions"]
    assert d["holes"] == [{"name": LEMMA_HOLE, "node": new}]


def test_the_generated_products_validate_and_carry_the_lemma(tmp_path: Path) -> None:
    """End to end over ``generate``: graph.json is v7 with the lemma, info.json says 3.36."""
    import json  # noqa: PLC0415

    root = with_lemma(tmp_path)
    built = products.generate(root, rendered_from="6" * 40, commit_time="2026-10-10T12:00:00Z")
    gdoc = json.loads(built.files[Path("targets") / TARGET / "graph.json"])
    [row] = [n for n in gdoc["nodes"] if n["node_id"] == ROOT_NODE]
    assert row["lemmas"] == [{"hole": LEMMA_HOLE, "node": LEMMA}]
    info = json.loads(built.files[Path("info.json")])
    assert info["protocol_version"] == "3.36" == products.PROTOCOL_VERSION
