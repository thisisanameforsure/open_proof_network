"""F30-T16 (the owner, 2026-10-22): every statement lives in one place, and superseded ones nowhere.

"Only things that are connected to the root node should be held on the LHS. They should live in one
place or the other, not both. Nodes that have been superseded do not need to be visible in the UI.
Specs need names and don't use the word spec, use speculative." Asked where the variants with no
line to the root go, the owner chose: a partial variant (a kernel-checked relation) on the left with
its own relation line into the root; a related variant (no proved relation) in the column.

Connected to the root means reached from it through the lines the tree draws at rest: a route to its
holes, a declared dependency, a variant's relation line (resolves, refutes, partial). A use (a proof
citing a statement) is not a connection: the cited statement keeps its column place and its line is
lit on hover. The column holds every statement not so connected that is speculative (a
``proposed_for`` pointer, or a revision of one) or a related variant, with its holes.
"""

from __future__ import annotations

import json
import re
from typing import Any

import refutes_fixture as rf
from test_crux_band import hrefs
from test_routes_view import node

from opn_gate import routes
from opn_site import dag, one_view

OLD, REV = "spec-x", "spec-x-v2"
PART, REL = "variant-part", "variant-rel"


def every_kind() -> dict[str, Any]:
    """``refutes_fixture`` with its refuting variant revised from a speculative statement (the live
    erdos-257 shape: ``spec-x`` superseded, ``spec-x-v2`` refutes, holes named after the old id),
    plus a partial variant and a related variant with a two-hole route."""
    text = json.dumps(rf.doc())
    for i in range(1, 6):
        text = text.replace(f'"{rf.VARIANT}--h{i}"', f'"{OLD}--h{i}"')
    text = text.replace(f'"{rf.VARIANT}"', f'"{REV}"')
    g: dict[str, Any] = json.loads(text)
    extra = [
        node(OLD, "superseded", origin="authored", deps=[f"{OLD}--h{i}" for i in range(1, 6)]),
        node(PART, "proved", origin="variant", relation="partial"),
        node(REL, origin="variant", relation="related", routes=[[f"{REL}--h1", f"{REL}--h2"]]),
        node(f"{REL}--h1", "proved"),
        node(f"{REL}--h2"),
    ]
    for r in extra:
        r.update(proposed_for=None, uses=[], label=r["node_id"], label_source="id")
    extra[0]["proposed_for"] = rf.ROOT
    g["nodes"].extend(extra)
    return g


def placed(g: dict[str, Any]) -> tuple[set[str], set[str], one_view.Drawing]:
    """(the left side at rest, the column, the drawing)."""
    vs = one_view.views(g, routes.read(g, []))
    d = one_view.drawing(g, [], href=hrefs(g), prefix=rf.ROOT)
    column = set(re.findall(r'data-node="([^"]+)"', d.band)) - set(
        re.findall(r'data-route="([^"]+)"', d.band)
    )
    left = {n for n in vs[one_view.ROUTES].nodes if "@" not in n}
    return left, column, d


def test_connected_statements_are_left_and_the_rest_in_the_column() -> None:
    left, column, _d = placed(every_kind())
    assert {rf.ROOT, f"{rf.ROOT}--h1", f"{rf.ROOT}--h2"} <= left
    assert {REV, f"{OLD}--h4", PART} <= left, "a refuting and a partial variant are connected"
    assert {rf.GAP, rf.UNIQUE, f"{rf.UNIQUE}--h1", REL, f"{REL}--h1", f"{REL}--h2"} <= column
    assert REV not in column and PART not in column


def test_every_statement_lives_in_exactly_one_place_and_superseded_in_none() -> None:
    g = every_kind()
    left, column, d = placed(g)
    live = {n["node_id"] for n in g["nodes"] if n["status"] != "superseded"}
    assert not left & column, left & column
    assert left | column == live, live - (left | column)
    assert OLD not in left | column
    assert f'data-node="{OLD}"' not in d.svg and f'data-node="{OLD}"' not in d.band
    assert d.hidden == 0 and d.toggle == "", "nothing is left over for a group of its own"


def test_a_partial_variant_draws_its_relation_line_into_the_root() -> None:
    vs = one_view.views(every_kind(), routes.read(every_kind(), []))
    assert (PART, rf.ROOT, f"{dag.RELATION_KIND} partial") in vs[one_view.ROUTES].lines


def test_the_set_through_the_refuting_variant_stays_on_the_left() -> None:
    """One place, not two: choosing the refuting set draws statements that are already on the left;
    the column holds none of them."""
    g = every_kind()
    vs = one_view.views(g, routes.read(g, []))
    view = vs[f"sel/refutes/{REV}@1"]
    _left, column, _d = placed(g)
    assert REV in view.nodes and not column & set(view.nodes)


def test_the_page_says_speculative_never_spec_or_proposed_statement() -> None:
    g = every_kind()
    d = one_view.drawing(g, [], href=hrefs(g), prefix=rf.ROOT)
    words = re.sub(r"<[^>]+>", " ", d.band)
    words = re.sub(r'data-[a-z-]+="[^"]*"', "", words)
    assert "Speculative statements" in d.band
    assert "Proposed statements" not in d.band
    assert not re.search(r"\bspecs?\b", re.sub(r"spec-[0-9a-z-]+", "", words), re.I)


def test_a_speculative_statement_a_related_variant_depends_on_stays_in_the_column() -> None:
    """Found on the live erdos-257 (2026-10-22): a related variant that declares uniqueness as a
    dependency took uniqueness out of the column (the old rule kept any declared crux in the tree),
    and since a related variant connects nothing to the root, uniqueness was in neither place. A
    dependency is a connection only when the statement that declares it is connected itself."""
    g = every_kind()
    for n in g["nodes"]:
        if n["node_id"] == REL:
            n["deps"] = [*n["deps"], rf.UNIQUE]
    left, column, _d = placed(g)
    assert rf.UNIQUE in column and rf.UNIQUE not in left
    live = {n["node_id"] for n in g["nodes"] if n["status"] != "superseded"}
    assert left | column == live and not left & column
