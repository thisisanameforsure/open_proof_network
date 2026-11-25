"""F27-T13 (R14; D-25 v3.51): the problem page draws a strictly harder route only on request.

Root ``t`` with two routes: ``[a]`` and ``[a, b, p]``, ``b`` open and ``p`` proved. The second
needs everything the first needs and ``b`` besides, so it is dominated with ``b`` and ``p``: off
the routes view and out of every set, in ``all`` with a class the stylesheet dims, counted by the
toggle with how many of them are proved, and named by the drawing's key.
"""

from __future__ import annotations

import re
from typing import Any

from test_one_view import classes, element
from test_routes_view import node

from opn_gate import routes
from opn_site import one_view, render


def harder_doc() -> dict[str, Any]:
    return {
        "schema": "graph/v16",
        "target_id": "t",
        "root": "t",
        "nodes": [
            node("t", origin="authored", routes=[["t--a"], ["t--a", "t--b", "t--p"]]),
            node("t--a"),
            node("t--b"),
            node("t--p", "proved"),
        ],
    }


def test_a_dominated_route_is_off_the_routes_view_and_in_no_set() -> None:
    g = harder_doc()
    vs = one_view.views(g, routes.read(g, []))
    assert {"t--b", "t--p", "t@2"} <= set(vs[one_view.ALL].nodes)
    assert not {"t--b", "t--p", "t@2"} & set(vs[one_view.ROUTES].nodes)
    assert {"t--a", "t@1"} <= set(vs[one_view.ROUTES].nodes)
    set_views = [v for k, v in vs.items() if k == one_view.TOP or k.startswith(("sel/", "edge/"))]
    assert set_views
    assert all(not {"t--b", "t--p"} & set(v.nodes) for v in set_views)


def test_the_toggle_counts_them_with_their_proved_and_the_key_names_the_mark() -> None:
    g = harder_doc()
    d = one_view.drawing(g, [], href={})
    assert d.hidden == 2 and d.harder == 2
    assert "Show 2 more statements (2 on strictly harder routes, 1 of them proved)" in d.toggle
    assert "harder" in classes(d.svg, "t--b") and "harder" in classes(d.svg, "t--p")
    assert "harder" not in classes(d.svg, "t--a")
    title = re.search(r"<title>(.*?)</title>", element(d.svg, "t--b")).group(1)  # type: ignore[union-attr]
    assert "strictly harder" in title
    junction = element(d.svg, "t@2")
    assert "strictly harder" in junction
    assert "harder" in d.marks
    assert "harder" in render.ROUTE_MARK_KEYS
    assert "harder" in render.GLOSSARY_BY_KEY


def test_nothing_dominated_changes_nothing() -> None:
    """A target with no strictly harder route draws as before: no mark, no count."""
    g = harder_doc()
    g["nodes"][0] = node("t", origin="authored", routes=[["t--a"], ["t--b", "t--p"]])
    d = one_view.drawing(g, [], href={})
    assert d.harder == 0 and "harder" not in d.marks
    assert "strictly harder" not in d.toggle
