"""The erdos-257 shape by hand (F30-T11, F04-T55; decisions v3.46), as the record will carry it
once the owner's revision gives ``spec-a70fcca4`` its ``refutes`` relation.

A ``graph.json`` document: root ``t`` with one route ``[t--h1 proved, t--h2 open]``; a
``refutes`` variant ``v`` with two routes, ``[v--h1, v--h2, v--h3 proved, v--h4 open]`` and
``[v--h5 open]``; a proved ``authored`` crux ``spec-gap`` proposed for the root, which the proved
hole ``t--h1`` *uses*; and a second proved crux ``spec-unique`` proposed for the root with its own
route ``[2 proved]`` that also uses ``spec-gap``. Nothing declares a crux as a dependency.

Read by ``opn_gate.routes`` (F27-T11, D-25 v3.46) it gives one proving set and two refuting
sets, and a selector whose top fork is by side: the proving set a leaf (``side: proves``), the
refuting family split on ``v`` (``side: refutes``) into its two leaves — ``result`` and ``tree``
assert that shape, so a test built on it fails here if the enumeration changes.
"""

from __future__ import annotations

from typing import Any

from test_routes_view import node

from opn_gate import routes

ROOT = "t"
VARIANT = "v"
GAP = "spec-gap"
UNIQUE = "spec-unique"
ROOT_LABEL = "Erdős problem 257"
PROVES = routes.PROVES


def doc() -> dict[str, Any]:
    rows = [
        node(
            ROOT,
            origin="authored",
            routes=[[f"{ROOT}--h1", f"{ROOT}--h2"]],
            approaches=["greedy walk"],
        ),
        node(f"{ROOT}--h1", "proved"),
        node(f"{ROOT}--h2"),
        node(
            VARIANT,
            origin="variant",
            relation=routes.REFUTES,
            routes=[[f"{VARIANT}--h{i}" for i in range(1, 5)], [f"{VARIANT}--h5"]],
            approaches=["the greedy walk for one half", "a different counterexample"],
        ),
        node(f"{VARIANT}--h1", "proved"),
        node(f"{VARIANT}--h2", "proved"),
        node(f"{VARIANT}--h3", "proved"),
        node(f"{VARIANT}--h4"),
        node(f"{VARIANT}--h5"),
        node(GAP, "proved", origin="authored"),
        node(
            UNIQUE,
            "proved",
            origin="authored",
            routes=[[f"{UNIQUE}--h1", f"{UNIQUE}--h2"]],
            approaches=["least element of the symmetric difference"],
        ),
        node(f"{UNIQUE}--h1", "proved"),
        node(f"{UNIQUE}--h2", "proved"),
    ]
    by_id = {r["node_id"]: r for r in rows}
    for r in rows:
        r["proposed_for"] = None
        r["uses"] = []
        r["label"] = r["node_id"]
        r["label_source"] = "id"
    by_id[ROOT]["label"], by_id[ROOT]["label_source"] = ROOT_LABEL, "gloss"
    by_id[GAP]["proposed_for"] = ROOT
    by_id[UNIQUE]["proposed_for"] = ROOT
    by_id[f"{ROOT}--h1"]["uses"] = [GAP]
    by_id[UNIQUE]["uses"] = [GAP]
    return {"schema": "graph/v14", "target_id": ROOT, "root": ROOT, "nodes": rows}


def result(graph: dict[str, Any] | None = None) -> routes.Routes:
    """The routes result as v3.46 publishes it, checked for the shape the tests rely on."""
    res = routes.read(graph or doc(), [])
    assert [s.settles for s in res.sets] == [PROVES, routes.REFUTES, routes.REFUTES]
    assert [s.variant for s in res.sets] == [None, VARIANT, VARIANT]
    return res


def tree(res: routes.Routes) -> routes.Selector:
    """The selector tree with the top fork by side (``side`` on the fork's two children)."""
    top = routes.selector_tree(res)
    assert (
        top.node is None
        and top.set is None
        and [c.side for c in top.children]
        == [
            PROVES,
            routes.REFUTES,
        ]
    )
    proving, refuting = top.children
    assert proving.set is not None and refuting.node == VARIANT and len(refuting.children) == 2
    return top
