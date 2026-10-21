"""F28-T1: closable nodes, read from a target's ``graph.json`` (draft decisions v3.41).

The case letters are the catalog's,
``engineering/session-notes/2026-10-15-proof-propagation-cases.md``. Graph documents are built
the way F27's tests build them and carry only the fields the reader uses. ``R <- [a, b]`` in a
docstring is a route of ``R`` whose holes became ``a`` and ``b``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from opn_gate import closing

FIXTURES = Path(__file__).parent / "fixtures" / "routes"


def node(
    node_id: str,
    status: str = "ready",
    *,
    deps: list[str] | None = None,
    origin: str = "authored",
    relation: str | None = None,
    decompositions: list[list[str | None]] | None = None,
    circular: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    return {
        "node_id": node_id,
        "status": status,
        "deps": deps or [],
        "origin": origin,
        "relation": relation,
        "decompositions": [
            {
                "partial": f"attempts/2026101{k}T000000Z-a-partial.lean",
                "annex": None,
                "holes": [{"name": f"h{i + 1}", "node": h} for i, h in enumerate(holes)],
            }
            for k, holes in enumerate(decompositions or [])
        ],
        "circular": circular or [],
    }


def hole(node_id: str, status: str = "ready", **kw: Any) -> dict[str, Any]:
    return node(node_id, status, origin="skeleton-hole", **kw)


def doc(*nodes: dict[str, Any], root: str = "t") -> dict[str, Any]:
    return {"schema": "graph/v9", "target_id": "t", "root": root, "nodes": list(nodes)}


def found(graph: dict[str, Any]) -> dict[str, tuple[str, str, tuple[str, ...], bool]]:
    """Each closable node as ``(link kind, link id, inputs, ready)``."""
    return {
        c.node: (c.link.kind, c.link.id, c.link.inputs, c.ready) for c in closing.closable(graph)
    }


def claim(hole_id: str, ancestor: str) -> dict[str, str]:
    return {"ancestor": ancestor, "claim": f"{hole_id}/defects/20261015T000000Z-x.json"}


def test_and_needs_every_hole() -> None:
    """A1: ``t <- [a]`` with ``a`` proved closes ``t``. A2: ``t <- [a, b]`` with ``b`` open closes
    nothing. A3: both proved closes it, both holes its inputs, in the route's order."""
    a1 = doc(node("t", decompositions=[["t--h1"]]), hole("t--h1", "proved"))
    assert found(a1) == {"t": ("route", "t@1", ("t--h1",), True)}
    a2 = doc(
        node("t", decompositions=[["t--h1", "t--h2"]]),
        hole("t--h1", "proved"),
        hole("t--h2"),
    )
    assert found(a2) == {}
    a3 = doc(
        node("t", decompositions=[["t--h1", "t--h2"]]),
        hole("t--h1", "proved"),
        hole("t--h2", "proved"),
    )
    assert found(a3) == {"t": ("route", "t@1", ("t--h1", "t--h2"), True)}


def test_or_takes_the_first_live_complete_route() -> None:
    """A4: either route closes; the second here. A5: both complete, the first in merge order.
    A6: a dead route beside a complete one does not block it. A7: a dead hole kills its route.
    And a ready route is taken before an earlier one that is only closable through a child."""
    a4 = doc(
        node("t", decompositions=[["t--h1"], ["t--h2"]]),
        hole("t--h1"),
        hole("t--h2", "proved"),
    )
    assert found(a4) == {"t": ("route", "t@2", ("t--h2",), True)}
    a5 = doc(
        node("t", decompositions=[["t--h1"], ["t--h2"]]),
        hole("t--h1", "proved"),
        hole("t--h2", "proved"),
    )
    assert found(a5)["t"][1] == "t@1"
    a6 = doc(
        node("t", decompositions=[["t--h1", "t--h2"], ["t--h3"]]),
        hole("t--h1", "proved"),
        hole("t--h2", "proved"),
        hole("t--h3", "refuted"),
    )
    assert found(a6) == {"t": ("route", "t@1", ("t--h1", "t--h2"), True)}
    a7 = doc(
        node("t", decompositions=[["t--h1", "t--h2"]]),
        hole("t--h1", "proved"),
        hole("t--h2", "refuted"),
    )
    assert found(a7) == {}
    ready_first = doc(
        node("t", decompositions=[["t--h1"], ["t--h2"]]),
        hole("t--h1", decompositions=[["t--h1--h1"]]),
        hole("t--h1--h1", "proved"),
        hole("t--h2", "proved"),
    )
    got = found(ready_first)
    assert got["t"] == ("route", "t@2", ("t--h2",), True)
    assert got["t--h1"] == ("route", "t--h1@1", ("t--h1--h1",), True)


def test_climbs_and_stops() -> None:
    """A8: ``R <- [P, q]``, ``P <- [a]``, ``a`` and ``q`` proved: ``P`` ready, ``R`` closable but
    not ready. A9: ``q`` open stops the climb at ``P``. A10: three levels from one proof. A11: AND
    and OR mixed at two levels."""
    a8 = doc(
        node("t", decompositions=[["t--h1", "t--h2"]]),
        hole("t--h1", decompositions=[["t--h1--h1"]]),
        hole("t--h1--h1", "proved"),
        hole("t--h2", "proved"),
    )
    assert found(a8) == {
        "t": ("route", "t@1", ("t--h1", "t--h2"), False),
        "t--h1": ("route", "t--h1@1", ("t--h1--h1",), True),
    }
    a9 = doc(
        node("t", decompositions=[["t--h1", "t--h2"]]),
        hole("t--h1", decompositions=[["t--h1--h1"]]),
        hole("t--h1--h1", "proved"),
        hole("t--h2"),
    )
    assert set(found(a9)) == {"t--h1"}
    a10 = doc(
        node("t", decompositions=[["t--h1"]]),
        hole("t--h1", decompositions=[["t--h1--h1"]]),
        hole("t--h1--h1", decompositions=[["t--h1--h1--h1"]]),
        hole("t--h1--h1--h1", "proved"),
    )
    got = found(a10)
    assert {k: v[3] for k, v in got.items()} == {
        "t": False,
        "t--h1": False,
        "t--h1--h1": True,
    }
    a11 = doc(
        node("t", decompositions=[["t--h1", "t--h2"], ["t--h3"]]),
        hole("t--h1", decompositions=[["t--h1--h1"], ["t--h1--h2", "t--h1--h3"]]),
        hole("t--h1--h1", "proved"),
        hole("t--h1--h2"),
        hole("t--h1--h3"),
        hole("t--h2", "proved"),
        hole("t--h3"),
    )
    got = found(a11)
    assert got["t--h1"] == ("route", "t--h1@1", ("t--h1--h1",), True)
    assert got["t"] == ("route", "t@1", ("t--h1", "t--h2"), False)


def test_shared_hole_and_diamond() -> None:
    """A12: one node in routes of two parents closes both. A13: a diamond reaches the root by two
    paths and lists it once."""
    a12 = doc(
        node("t", decompositions=[["t--h1", "t--h2"]]),
        hole("t--h1", decompositions=[["x"]]),
        hole("t--h2", decompositions=[["x"]]),
        node("x", "proved"),
    )
    got = found(a12)
    assert got["t--h1"] == ("route", "t--h1@1", ("x",), True)
    assert got["t--h2"] == ("route", "t--h2@1", ("x",), True)
    assert got["t"] == ("route", "t@1", ("t--h1", "t--h2"), False)
    assert [c.node for c in closing.closable(a12)].count("t") == 1


def test_nothing_closes_that_should_not() -> None:
    """A14: a proved node is never closable. A15: a superseded hole is followed to its revision.
    A16: a superseded hole whose revision is open closes nothing. A17: a cycle closes nothing on its
    own. A18: unresolved holes close nothing. And a dead parent is never closable."""
    a14 = doc(node("t", "proved", decompositions=[["t--h1"]]), hole("t--h1", "proved"))
    assert found(a14) == {}
    a15 = doc(
        node("t", deps=["t--h1-v2"], decompositions=[["t--h1"]]),
        hole("t--h1", "superseded"),
        hole("t--h1-v2", "proved"),
    )
    assert found(a15) == {"t": ("route", "t@1", ("t--h1-v2",), True)}
    a16 = doc(
        node("t", deps=["t--h1-v2"], decompositions=[["t--h1"]]),
        hole("t--h1", "superseded"),
        hole("t--h1-v2"),
    )
    assert found(a16) == {}
    a17 = doc(
        node("t", decompositions=[["t--h1"]]),
        hole("t--h1", decompositions=[["t"]]),
    )
    assert found(a17) == {}
    a18 = doc(
        node("t", decompositions=[[None], [None]]),
        hole("t--h1", "proved"),
        hole("t--h2", "proved"),
    )
    assert found(a18) == {}
    dead = doc(node("t", "abandoned", decompositions=[["t--h1"]]), hole("t--h1", "proved"))
    assert found(dead) == {}


def test_lemma_hole_counts_the_node_it_names() -> None:
    """A19: a hole that restated a node under another branch became that node (a lemma edge,
    D-12 v3.38); its proof closes the route."""
    a19 = doc(
        node("t", decompositions=[["t--h1", "t--h2"]]),
        hole("t--h1", "proved"),
        hole("t--h2", decompositions=[["t--h1"]]),
    )
    got = found(a19)
    assert got["t--h2"] == ("route", "t--h2@1", ("t--h1",), True)
    assert got["t"] == ("route", "t@1", ("t--h1", "t--h2"), False)


def test_a_circularity_claim_is_no_link() -> None:
    """A20, restated for D-12 v3.42 (F08-T42): ``t <- [m]``, ``m <- [h, g]``, ``h`` carries a
    merged claim that it implies ``t``. F28-T1 made ``t`` closable through the claim once ``h`` was
    proved with ``g`` still open; the claim is retired with that link, so ``t`` closes only through
    a route, which needs ``g`` too. Nothing is closable in any of the three shapes."""
    graph = doc(
        node("t", decompositions=[["t--h1"]]),
        hole("t--h1", decompositions=[["t--h1--h1", "t--h1--h2"]]),
        hole("t--h1--h1", "proved", circular=[claim("t--h1--h1", "t")]),
        hole("t--h1--h2"),
    )
    assert found(graph) == {}
    open_hole = doc(
        node("t", decompositions=[["t--h1"]]),
        hole("t--h1", decompositions=[["t--h1--h1", "t--h1--h2"]]),
        hole("t--h1--h1", circular=[claim("t--h1--h1", "t")]),
        hole("t--h1--h2"),
    )
    assert found(open_hole) == {}
    borrowed = doc(
        node("t", decompositions=[["t--h1"]]),
        hole("t--h1", decompositions=[["t--h1--h1", "t--h1--h2"]]),
        hole("t--h1--h1"),
        hole("t--h1--h2", "proved", circular=[claim("t--h1--h1", "t")]),
    )
    assert found(borrowed) == {}


def test_root_closes_by_climb_or_variant() -> None:
    """A21: a proved ``resolves`` variant makes the root closable and ready; one closable only
    through its own route makes the root closable, not ready. A ``related`` variant is no link.
    A22: the climb reaches the root."""
    variant = doc(node("t"), node("v", "proved", relation="resolves"))
    assert found(variant) == {"t": ("variant", "v", ("v",), True)}
    related = doc(node("t"), node("v", "proved", relation="related"))
    assert found(related) == {}
    through = doc(
        node("t"),
        node("v", relation="resolves", decompositions=[["v--h1"]]),
        hole("v--h1", "proved"),
    )
    assert found(through) == {
        "t": ("variant", "v", ("v",), False),
        "v": ("route", "v@1", ("v--h1",), True),
    }
    a22 = doc(
        node("t", decompositions=[["t--h1"]]),
        hole("t--h1", decompositions=[["t--h1--h1"]]),
        hole("t--h1--h1", "proved"),
    )
    assert found(a22)["t"] == ("route", "t@1", ("t--h1",), False)


def test_output_is_in_record_order_and_round_trips() -> None:
    graph = doc(
        node("t", decompositions=[["t--h1", "t--h2"]]),
        hole("t--h1", decompositions=[["x"]]),
        hole("t--h2", decompositions=[["x"]]),
        node("x", "proved"),
    )
    got = closing.closable(graph)
    assert [c.node for c in got] == ["t", "t--h1", "t--h2"]
    assert json.loads(json.dumps([c.as_dict() for c in got]))[0] == {
        "node": "t",
        "link": {"kind": "route", "id": "t@1", "inputs": ["t--h1", "t--h2"], "verdict": "proved"},
        "ready": False,
    }


def test_live_erdos_1094() -> None:
    """AC9: the graph as it stood at edadad318 (2026-10-15), F27's fixture: exactly the node the
    owner asked about is closable, ready, through its one route."""
    live = json.loads((FIXTURES / "erdos-1094-20261015.json").read_text(encoding="utf-8"))
    assert found(live["graph"]) == {
        "erdos-1094--h2--h2--h2--h2": (
            "route",
            "erdos-1094--h2--h2--h2--h2@1",
            ("erdos-1094--h2--h2--h2--h2--h1",),
            True,
        )
    }
