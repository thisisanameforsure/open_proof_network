"""F27-T1: routes and sufficient sets read from a target's products (D-25 v3.40).

Synthetic graph documents carry only the fields the reader uses (``graph/v4`` on). The two live
fixtures in ``fixtures/routes/`` are erdos-1094 and erdos-69 as the graph published them at
commit 6c3a33886 (2026-10-14): ``graph.json`` with each node's ``node_id``, ``status``, ``cause``,
``deps``, ``origin``, ``relation``, ``decompositions`` (annex dropped), ``circular`` and
``lemmas``, and the target's ``frontier.json`` entries with their counts and ``ready_since``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from opn_gate import routes

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
    proofs: list[list[str] | None] | None = None,
    uses: list[str] | None = None,
    lemmas: list[str] | None = None,
) -> dict[str, Any]:
    """``proofs`` (F27-T9): one entry per merged proof, each the nodes its term ``used`` as
    graph/v4 publishes them, or ``None`` where nothing measured it (an older merge); ``uses``
    (F08-R19) and ``lemmas`` (D-12 v3.38) as the row carries them."""
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
        "proofs": [
            {
                "kind": "proof" if k == 0 else "alternate",
                "path": "Proof.lean" if k == 0 else f"alternates/{k}.lean",
                "artifact_hash": f"{k:064x}",
                "attestation": f"{k + 1:06d}.json",
                "merge_commit": f"{k:040x}",
                "submitter": None,
                "used": used,
            }
            for k, used in enumerate(proofs or [])
        ],
        "uses": uses or [],
        "lemmas": [{"hole": f"l{i + 1}", "node": n} for i, n in enumerate(lemmas or [])],
    }


def hole(node_id: str, status: str = "ready", **kw: Any) -> dict[str, Any]:
    return node(node_id, status, origin="skeleton-hole", **kw)


def doc(*nodes: dict[str, Any], root: str = "t") -> dict[str, Any]:
    return {"schema": "graph/v9", "target_id": "t", "root": root, "nodes": list(nodes)}


def open_sets(result: routes.Routes) -> list[list[str]]:
    return [list(s.open) for s in result.sets]


def closes_root(graph: dict[str, Any], members: set[str]) -> bool:
    """An independent check of R5: forward-chain from the set's statements taken as proved (with
    every node the graph already proves) through routes, direct proofs with their declared
    dependencies, and resolves variants, and ask whether the root closes. Assemblies are assumed
    submitted, which is what a set's ``assemblies`` names."""
    rows = {str(n["node_id"]): n for n in graph["nodes"]}
    closed = {k for k, n in rows.items() if n["status"] == "proved"} | set(members)
    changed = True
    while changed:
        changed = False
        for k, n in rows.items():
            if k in closed:
                continue
            for d in n.get("decompositions") or []:
                hs = [h["node"] for h in d["holes"]]
                if hs and all(h is not None and h in closed for h in hs):
                    closed.add(k)
                    changed = True
                    break
    root = str(graph["root"])
    if root in closed:
        return True
    return any(
        n.get("relation") == "resolves" and k in closed for k, n in rows.items() if k != root
    )


# --- R5: the AND-OR enumeration ------------------------------------------------------------


def test_a_root_with_no_routes_is_its_own_set() -> None:
    result = routes.read(doc(node("t")))
    assert result.routes == ()
    assert open_sets(result) == [["t"]]
    assert result.sets[0].assemblies == ()


def test_and_takes_every_hole_of_a_route() -> None:
    g = doc(
        node("t", deps=["t--h1", "t--h2"], decompositions=[["t--h1", "t--h2"]]),
        hole("t--h1"),
        hole("t--h2", "proved"),
    )
    result = routes.read(g)
    (s,) = result.sets
    assert s.open == ("t--h1",)
    assert s.proved == ("t--h2",)
    assert s.statements == ("t--h1", "t--h2")
    assert s.assemblies == ("t",)
    assert s.routes == ("t@1",)
    assert (s.total, s.closed, s.remaining) == (2, 1, 1)


def test_or_gives_one_set_per_route() -> None:
    """AC1: two routes of the root share a hole; one set each, the shared hole in both."""
    g = doc(
        node(
            "t",
            deps=["t--h1", "t--h2", "t--h3"],
            decompositions=[["t--h1", "t--h2"], ["t--h1", "t--h3"]],
        ),
        hole("t--h1"),
        hole("t--h2"),
        hole("t--h3"),
    )
    result = routes.read(g)
    assert open_sets(result) == [["t--h1", "t--h2"], ["t--h1", "t--h3"]]
    assert [s.routes for s in result.sets] == [("t@1",), ("t@2",)]
    assert [s.shared for s in result.sets] == [1, 1]
    assert result.sets[0].id != result.sets[1].id


def test_and_expands_through_nested_routes() -> None:
    """AC2: a decomposed hole is expanded; the set holds the grandchildren and names the hole
    an assembly beside the root."""
    g = doc(
        node("t", deps=["t--h1", "t--h2"], decompositions=[["t--h1", "t--h2"]]),
        hole("t--h1", deps=["t--h1--h1", "t--h1--h2"], decompositions=[["t--h1--h1", "t--h1--h2"]]),
        hole("t--h1--h1"),
        hole("t--h1--h2", "proved"),
        hole("t--h2"),
    )
    (s,) = routes.read(g).sets
    assert s.open == ("t--h1--h1", "t--h2")
    assert s.proved == ("t--h1--h2",)
    assert s.assemblies == ("t", "t--h1")
    assert s.routes == ("t@1", "t--h1@1")
    assert closes_root(g, set(s.statements))


def test_proved_interior_node_cuts_its_descendants() -> None:
    """AC3: a decomposed hole proved directly ends the cut; its own holes are in no set."""
    g = doc(
        node("t", deps=["t--h1", "t--h2"], decompositions=[["t--h1", "t--h2"]]),
        hole("t--h1", "proved", deps=["t--h1--h1"], decompositions=[["t--h1--h1"]]),
        hole("t--h1--h1"),
        hole("t--h2"),
    )
    (s,) = routes.read(g).sets
    assert s.statements == ("t--h1", "t--h2")
    assert s.proved == ("t--h1",)
    assert "t--h1--h1" not in s.statements
    assert s.assemblies == ("t",)


def test_dead_route_contributes_no_set() -> None:
    """AC4: a refuted hole kills its route; the other route stands; the summary counts it."""
    g = doc(
        node(
            "t",
            deps=["t--h1", "t--h2", "t--h3"],
            decompositions=[["t--h1", "t--h2"], ["t--h3"]],
        ),
        hole("t--h1", "refuted"),
        hole("t--h2"),
        hole("t--h3"),
    )
    result = routes.read(g)
    assert open_sets(result) == [["t--h3"]]
    first = result.routes[0]
    assert first.id == "t@1"
    assert first.live is False
    assert (first.summary.holes, first.summary.dead, first.summary.open) == (2, 1, 1)


def test_every_route_dead_falls_back_to_a_direct_proof() -> None:
    g = doc(
        node("t", deps=["t--h1"], decompositions=[["t--h1"]]),
        hole("t--h1", "abandoned"),
    )
    (s,) = routes.read(g).sets
    assert s.open == ("t",)
    assert s.assemblies == ()


def test_direct_proof_needs_its_declared_dependencies() -> None:
    """A node taken directly brings its non-hole deps, which a proof of it waits on (D-3)."""
    g = doc(node("t", deps=["lemma"]), node("lemma"))
    (s,) = routes.read(g).sets
    assert s.open == ("lemma", "t")


def test_cycle_through_a_lemma_is_dropped() -> None:
    g = doc(
        node("t", deps=["t--h1"], decompositions=[["t--h1"]]),
        hole("t--h1", decompositions=[["t"]]),
    )
    (s,) = routes.read(g).sets
    assert s.open == ("t--h1",)


def test_resolves_variant_is_an_alternative() -> None:
    """AC6 (Q5): a resolves variant closes the target; partial and related variants do not."""
    g = doc(
        node("t"),
        node("v-res", origin="variant", relation="resolves"),
        node("v-part", origin="variant", relation="partial"),
        node("v-rel", origin="variant", relation="related"),
    )
    result = routes.read(g)
    assert open_sets(result) == [["t"], ["v-res"]]
    assert [s.variant for s in result.sets] == [None, "v-res"]


def test_proved_root_is_one_closed_set() -> None:
    g = doc(node("t", "proved", deps=["t--h1"], decompositions=[["t--h1"]]), hole("t--h1"))
    (s,) = routes.read(g).sets
    assert (s.statements, s.open, s.remaining) == (("t",), (), 0)


def test_every_statement_proved_leaves_the_assemblies() -> None:
    """Q3: holes proved do not close the parent (D-12 v3.19); the set names what to submit."""
    g = doc(
        node("t", deps=["t--h1"], decompositions=[["t--h1"]]),
        hole("t--h1", "proved"),
    )
    (s,) = routes.read(g).sets
    assert (s.remaining, s.assemblies) == (0, ("t",))


# --- R6: minimality -------------------------------------------------------------------------


def test_finest_keeps_every_full_expansion_any_drops_the_dominated() -> None:
    """F27-T7 (the owner, 2026-10-15: show every set that goes all the way to the leaves): each
    choice of routes is a finest set, even one needing strictly more than another; only the
    coarser cuts (``cut: any``) drop a dominated set."""
    g = doc(
        node("t", deps=["t--h1", "t--h2"], decompositions=[["t--h1", "t--h2"]]),
        hole("t--h1"),
        hole(
            "t--h2",
            deps=["t--h2--h1", "t--h2--h2"],
            decompositions=[["t--h1"], ["t--h2--h1", "t--h2--h2"]],
        ),
        hole("t--h2--h1"),
        hole("t--h2--h2"),
    )
    assert open_sets(routes.read(g)) == [["t--h1"], ["t--h1", "t--h2--h1", "t--h2--h2"]]
    assert ["t--h1", "t--h2--h1", "t--h2--h2"] not in open_sets(routes.read(g, cut="any"))


# --- R2, R3: reading the record ---------------------------------------------------------------


def test_unnamed_holes_assigned_or_unresolved() -> None:
    """AC5: one route with unnamed holes takes the untaken hole children; two cannot."""
    one = doc(
        node("t", deps=["t--h1-v2", "t--h2"], decompositions=[[None, None]]),
        hole("t--h1-v2", "proved"),
        hole("t--h2"),
    )
    result = routes.read(one)
    assert result.routes[0].resolved is True
    assert [h.node for h in result.routes[0].holes] == ["t--h1-v2", "t--h2"]
    assert open_sets(result) == [["t--h2"]]

    two = doc(
        node("t", deps=["t--h1", "t--h2"], decompositions=[[None], [None]]),
        hole("t--h1"),
        hole("t--h2"),
    )
    result = routes.read(two)
    assert [r.resolved for r in result.routes] == [False, False]
    assert [r.summary.unresolved for r in result.routes] == [1, 1]
    assert open_sets(result) == [["t"]]  # neither route is used; the root is taken directly


def test_a_superseded_hole_is_followed_to_its_revision() -> None:
    g = doc(
        node("t", deps=["t--h1-v2"], decompositions=[["t--h1"]]),
        hole("t--h1", "superseded"),
        hole("t--h1-v2"),
    )
    result = routes.read(g)
    assert result.routes[0].holes[0].node == "t--h1-v2"
    assert open_sets(result) == [["t--h1-v2"]]


# --- R4: route facts ------------------------------------------------------------------------


def test_route_summary_aggregates_the_frontier_facts() -> None:
    g = doc(
        node(
            "t",
            deps=["t--h1", "t--h2", "t--h3"],
            decompositions=[["t--h1", "t--h2", "t--h3"]],
        ),
        hole("t--h1", "proved"),
        hole("t--h2", deps=["t--h2--h1"], decompositions=[["t--h2--h1"]]),
        hole("t--h2--h1"),
        hole("t--h3"),
    )
    entries = [
        {
            "node_id": "t--h2",
            "attempts": 3,
            "refuted_route_classes": ["sieve"],
            "ready_since": "2026-10-09T12:00:00Z",
        },
        {
            "node_id": "t--h3",
            "attempts": 0,
            "refuted_route_classes": [],
            "ready_since": "2026-10-08T13:03:06Z",
        },
        {
            "node_id": "t--h2--h1",
            "attempts": 5,
            "refuted_route_classes": ["induction"],
            "ready_since": "2026-10-10T00:00:00Z",
        },
    ]
    result = routes.read(g, entries)
    top = result.routes[0]
    s = top.summary
    assert (s.holes, s.proved, s.open, s.dead, s.unresolved) == (3, 1, 2, 0, 0)
    assert (s.attempts, s.unattempted) == (3, 1)
    assert s.refuted_route_classes == ("sieve",)
    assert s.oldest_open_since == "2026-10-08T13:03:06Z"
    h2 = next(h for h in top.holes if h.node == "t--h2")
    assert (h2.status, h2.attempts, h2.routes) == ("ready", 3, 1)
    proved = next(h for h in top.holes if h.node == "t--h1")
    assert proved.attempts is None  # not on the frontier: nothing published to repeat


def test_entries_of_another_target_are_ignored() -> None:
    g = doc(node("t", deps=["t--h1"], decompositions=[["t--h1"]]), hole("t--h1"))
    entries = [
        {
            "node_id": "t--h1",
            "target_id": "other",
            "attempts": 9,
            "refuted_route_classes": [],
            "ready_since": None,
        }
    ]
    assert routes.read(g, entries).routes[0].summary.attempts == 0


def test_an_older_graphs_circular_field_marks_nothing() -> None:
    """Q6 restated for D-12 v3.43 (F08-T42): a graph rendered before graph/v11 may carry a row's
    ``circular`` label; a set keeps the statement and says nothing of it."""
    g = doc(
        node("t", deps=["t--h1"], decompositions=[["t--h1"]]),
        hole("t--h1", circular=[{"ancestor": "t", "claim": "t--h1/defects/x.yaml"}]),
    )
    (s,) = routes.read(g).sets
    assert s.open == ("t--h1",)
    assert "circular" not in s.as_dict()


# --- R8: the coarser cuts ------------------------------------------------------------------


def test_any_cut_adds_coarser_sets_up_to_cap() -> None:
    """AC7: with cut ``any`` the root taken directly is a set, so is the hole taken directly in
    place of its route; every set minimal; a cap below the count truncates and says so."""
    g = doc(
        node("t", deps=["t--h1", "t--h2"], decompositions=[["t--h1", "t--h2"]]),
        hole("t--h1", deps=["t--h1--h1"], decompositions=[["t--h1--h1"]]),
        hole("t--h1--h1"),
        hole("t--h2"),
    )
    finest = routes.read(g)
    assert open_sets(finest) == [["t--h1--h1", "t--h2"]]
    coarse = routes.read(g, cut="any")
    assert coarse.cut == "any"
    assert sorted(open_sets(coarse)) == [["t"], ["t--h1", "t--h2"], ["t--h1--h1", "t--h2"]]
    assert coarse.truncated is False
    capped = routes.read(g, cut="any", max_sets=2)
    assert capped.truncated is True
    assert len(capped.sets) <= 2


def test_unknown_cut_is_refused() -> None:
    with pytest.raises(ValueError, match="cut"):
        routes.read(doc(node("t")), cut="widest")


def test_as_dict_round_trips_through_json() -> None:
    g = doc(node("t", deps=["t--h1"], decompositions=[["t--h1"]]), hole("t--h1"))
    out = routes.read(g).as_dict()
    assert json.loads(json.dumps(out)) == out
    assert set(out) == {"target_id", "root", "cut", "at_proved", "truncated", "routes", "sets"}
    assert set(out["sets"][0]) >= {
        "id",
        "statements",
        "open",
        "proved",
        "assemblies",
        "routes",
        "proof_routes",
        "variant",
        "total",
        "closed",
        "remaining",
        "shared",
    }
    assert "circular" not in out["sets"][0]  # F08-T42 (D-12 v3.43)


# --- F27-T9 (R13): following a proved statement's proof --------------------------------------


def followed_doc() -> dict[str, Any]:
    """Root ``t`` with two routes, ``[a, p]`` and ``[q]``. ``p`` is proved and decomposed into
    ``[p--h1, p--h2]``, both proved, but its proof's term used ``p--h1`` alone: the proof went
    past the route. ``q`` is proved and its term used both holes of its one route: the proof
    is the route's assembly."""
    return doc(
        node("t", decompositions=[["t--a", "t--p"], ["t--q"]]),
        node("t--a"),
        node(
            "t--p",
            "proved",
            deps=["t--p--h1", "t--p--h2"],
            decompositions=[["t--p--h1", "t--p--h2"]],
            proofs=[["t--p--h1"]],
        ),
        hole("t--p--h1", "proved", proofs=[[]]),
        hole("t--p--h2", "proved", proofs=[[]]),
        node(
            "t--q",
            "proved",
            deps=["t--q--h1", "t--q--h2"],
            decompositions=[["t--q--h1", "t--q--h2"]],
            proofs=[["t--q--h1", "t--q--h2"]],
        ),
        hole("t--q--h1", "proved", proofs=[[]]),
        hole("t--q--h2", "proved", proofs=[[]]),
    )


def test_follow_adds_what_each_proved_member_rests_on_and_changes_no_set() -> None:
    """R13: with ``at_proved: follow`` every proved statement of a set is expanded along its
    first proof's term (F18, ``used``), so the set shows the proved structure it rests on; the
    sets themselves — their ids, open statements, assemblies, routes and order — are those of
    the default, which stops at a proved statement (R5)."""
    g = followed_doc()
    stop = routes.read(g, [])
    follow = routes.read(g, [], at_proved="follow")
    assert (stop.at_proved, follow.at_proved) == ("stop", "follow")
    assert [s.id for s in stop.sets] == [s.id for s in follow.sets]
    assert open_sets(stop) == open_sets(follow) == [["t--a"], []]
    assert [(s.assemblies, s.routes) for s in stop.sets] == [
        (s.assemblies, s.routes) for s in follow.sets
    ]
    assert routes.selector_tree(stop).as_dict() == routes.selector_tree(follow).as_dict()
    assert [s.statements for s in stop.sets] == [("t--a", "t--p"), ("t--q",)]
    # p's proof used p--h1 alone: p--h1 joins, p--h2 does not, and no route is followed
    assert follow.sets[0].statements == ("t--a", "t--p", "t--p--h1")
    assert follow.sets[0].proved == ("t--p", "t--p--h1")
    assert follow.sets[0].proof_routes == ()
    # q's proof used both holes of its route: the route is the proof's own structure
    assert follow.sets[1].statements == ("t--q", "t--q--h1", "t--q--h2")
    assert follow.sets[1].proof_routes == ("t--q@1",)
    assert (follow.sets[1].closed, follow.sets[1].remaining) == (3, 0)
    assert all(s.proof_routes == () for s in stop.sets)
    for s in follow.sets:
        assert closes_root(g, set(s.statements)), s.id


def test_followed_names_the_routes_a_proof_went_through_and_its_direct_uses() -> None:
    """The structure the page draws beneath a proved statement: the nodes its proof rests on
    (transitively), the routes it went through (every hole of the route among what its node's
    proof used) and the direct lines, from a used node to its user, that no followed route
    carries."""
    g = followed_doc()
    result = routes.read(g, [])
    p = routes.followed(result, g, "t--p")
    assert (p.nodes, p.routes, p.lines) == (("t--p--h1",), (), (("t--p--h1", "t--p"),))
    q = routes.followed(result, g, "t--q")
    assert (q.nodes, q.routes, q.lines) == (("t--q--h1", "t--q--h2"), ("t--q@1",), ())


def test_an_unmeasured_proof_follows_its_declared_dependencies_uses_and_lemmas() -> None:
    """A proof merged before the gate measured its term (``used: null``, F18-R2) is followed
    along everything it could rest on — its deps, its uses and its lemmas — as the products'
    closure is (``NodeFacts.rests_on``)."""
    g = doc(
        node("t", decompositions=[["t--p"]]),
        hole(
            "t--p",
            "proved",
            deps=["t--d"],
            uses=["t--u"],
            lemmas=["t--l"],
            proofs=[None],
        ),
        node("t--d", "proved", proofs=[[]]),
        node("t--u", "proved", proofs=[["t--w"]]),
        node("t--w", "proved", proofs=[[]]),
        node("t--l", "proved", proofs=[[]]),
    )
    follow = routes.read(g, [], at_proved="follow")
    (s,) = follow.sets
    assert s.statements == ("t--d", "t--l", "t--p", "t--u", "t--w")
    f = routes.followed(routes.read(g, []), g, "t--p")
    assert f.nodes == ("t--d", "t--l", "t--u", "t--w")
    assert f.lines == (("t--d", "t--p"), ("t--l", "t--p"), ("t--u", "t--p"), ("t--w", "t--u"))


def test_following_a_malformed_record_terminates() -> None:
    """Two proofs that cite each other cannot come from the gate (a used node was proved before
    its user merged), but a hand-made product could say so; the walk sees each node once."""
    g = doc(
        node("t", decompositions=[["t--p"]]),
        hole("t--p", "proved", proofs=[["t--q", "nowhere"]]),
        node("t--q", "proved", proofs=[["t--p"]]),
    )
    follow = routes.read(g, [], at_proved="follow")
    assert follow.sets[0].statements == ("t--p", "t--q")


def test_unknown_at_proved_is_refused() -> None:
    with pytest.raises(ValueError, match="at_proved"):
        routes.read(doc(node("t")), at_proved="through")


def test_follow_on_live_erdos_1094_changes_no_set_and_adds_only_proved_statements() -> None:
    """erdos-1094 as published on 2026-10-19 (graph 00f4bc884): seven of its proved statements
    rest on others, five of them proved by closure (F28). Following them adds proved statements
    beneath every set that holds one, keeps every id, open set, assembly, route and the selector
    tree, and each set still closes the root."""
    graph, entries = live("erdos-1094-20261019")
    stop = routes.read(graph, entries)
    follow = routes.read(graph, entries, at_proved="follow")
    assert [s.id for s in stop.sets] == [s.id for s in follow.sets]
    assert open_sets(stop) == open_sets(follow)
    assert [(s.assemblies, s.routes, s.variant) for s in stop.sets] == [
        (s.assemblies, s.routes, s.variant) for s in follow.sets
    ]
    assert routes.selector_tree(stop).as_dict() == routes.selector_tree(follow).as_dict()
    rows = {str(n["node_id"]): n for n in graph["nodes"]}
    grew = 0
    for a, b in zip(stop.sets, follow.sets, strict=True):
        added = set(b.statements) - set(a.statements)
        assert all(rows[m]["status"] == "proved" for m in added), (b.id, added)
        assert set(a.statements) <= set(b.statements)
        grew += len(added)
        assert closes_root(graph, set(b.statements)), b.id
    assert grew > 0
    deep = "erdos-1094--h2--h2--h2--h3--h1--h1--h1"  # proved, three closures above it
    assert any(deep in s.statements for s in follow.sets)
    assert not any(deep in s.statements for s in stop.sets)


# --- AC8: the live shapes -------------------------------------------------------------------


def live(name: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    data = json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))
    return data["graph"], data["frontier_entries"]


def test_live_shape_sets_close_the_root() -> None:
    """AC8: erdos-1094 as published on 2026-10-14 — every route resolves, the finest sets are
    minimal, and each closes the root by the independent check."""
    graph, entries = live("erdos-1094")
    result = routes.read(graph, entries)
    assert len(result.routes) == 16
    assert all(r.resolved for r in result.routes)
    assert len(result.sets) == 4  # two statements with two live routes each: 2 x 2
    assert len({s.id for s in result.sets}) == 4
    for s in result.sets:
        assert closes_root(graph, set(s.statements)), s.id
    coarse = routes.read(graph, entries, cut="any")
    assert len(coarse.sets) > len(result.sets)
    for s in coarse.sets:
        assert closes_root(graph, set(s.statements)), s.id


def test_live_shape_with_unnamed_holes() -> None:
    """erdos-69's root decomposition predates named holes (its holes read ``node: null``); the
    two hole children, both revisions, are its holes."""
    graph, entries = live("erdos-69")
    result = routes.read(graph, entries)
    root_route = next(r for r in result.routes if r.node == "erdos-69")
    assert root_route.resolved
    assert {h.node for h in root_route.holes} == {"erdos-69--h1-v2", "erdos-69--h2-v2"}
    (s,) = result.sets
    assert s.open == ("erdos-69--h2-v2--h1-v2--h4",)
    assert s.assemblies == ("erdos-69", "erdos-69--h2-v2", "erdos-69--h2-v2--h1-v2")


def test_cap_counts_minimal_sets_not_intermediate_combinations() -> None:
    """F27-T6: erdos-1094 as published on 2026-10-15 (graph edadad318) has 293 minimal coarser
    sets, but the combinations met on the way exceed the default cap; the live tool answered 58
    and ``truncated``. Dominated options are dropped at every node, which is safe because a
    dominated option stays dominated under any union, so the cap meets only minimal sets."""
    graph, entries = live("erdos-1094-20261015")
    unbounded = routes.read(graph, entries, cut="any", max_sets=10**6)
    assert (len(unbounded.sets), unbounded.truncated) == (293, False)
    default = routes.read(graph, entries, cut="any")
    assert default.truncated is False
    assert [s.id for s in default.sets] == [s.id for s in unbounded.sets]
    for s in default.sets:
        assert closes_root(graph, set(s.statements)), s.id


def test_finest_sets_reach_the_leaves() -> None:
    """F27-T7: on erdos-1094 of 2026-10-15 every finest set is a full expansion — each of its
    open statements has no live route of its own, so nothing in it could be expanded further —
    and there is one per combination of route choices (h2--h1 and h3 have two live routes each)."""
    graph, entries = live("erdos-1094-20261015")
    result = routes.read(graph, entries)
    expandable = {r.node for r in result.routes if r.live}
    assert len(result.sets) == 4
    for s in result.sets:
        assert not set(s.open) & expandable, s.id
        assert closes_root(graph, set(s.statements)), s.id
