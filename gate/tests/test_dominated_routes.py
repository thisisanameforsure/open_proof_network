"""F27-T12 (R14; D-25 v3.52): a route that is strictly harder than another is not offered.

A sufficient set *needs* its open members; its assemblies add nothing, because the network
closes each once its inputs are proved (D-12 v3.42). A set is dominated when another set of its
side needs a proper subset of what it needs; a route or a statement that appears only in
dominated sets is dominated. The sets leave dominated ones out,
and the frontier omits dominated statements. Equal needs are not harder: both are offered. A
statement a kept set's proved member's proof rests on is never dominated. A capped enumeration
leaves out nothing.

The live fixture is erdos-1094 as graph 257feba234 published it (2026-11-24), trimmed to the
fields the reader uses. Its expectations come from an independent expansion to open leaves
(the owner's question of 2026-11-25): every proof of the root needs Baker-Harman-Pintz
(``--h2--h2--h1--h1``), which also closes the small range through ``--h3@2``, so the residue
sieve, Granville-Ramaré, the n/gcd split and the strip only add work.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from harness import TARGET
from shelving_support import ROOT, A, T, Tree, make_keys
from test_target_routes import doc, hole, node, open_sets

from opn_gate import products, routes

FIXTURES = Path(__file__).parent / "fixtures" / "routes"


def strictly_more() -> dict[str, Any]:
    """The F27-T7 shape: ``t--h2``'s second route needs ``t--h2--h1`` and ``t--h2--h2`` where
    its first needs only ``t--h1``, which the root needs anyway."""
    return doc(
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


# --- the sets -----------------------------------------------------------------------------------


def test_a_set_needing_strictly_more_is_not_offered() -> None:
    g = strictly_more()
    assert open_sets(routes.read(g)) == [["t--h1"]]
    d = routes.dominated(g)
    assert d.truncated is False
    assert d.routes == frozenset({"t--h2@2"})
    assert d.statements == frozenset({"t--h2--h1", "t--h2--h2"})


def test_domination_is_judged_across_the_whole_target() -> None:
    """At ``b`` alone neither route contains the other: ``{x}`` against ``{y, z}``. But the
    root needs ``x`` through ``a`` whichever way ``b`` goes, so ``b@2`` only adds work."""
    g = doc(
        node("t", deps=["a", "b"], decompositions=[["a", "b"]]),
        node("a", deps=["x"], decompositions=[["x"]]),
        node("b", deps=["x", "y", "z"], decompositions=[["x"], ["y", "z"]]),
        node("x"),
        node("y"),
        node("z"),
    )
    assert open_sets(routes.read(g)) == [["x"]]
    d = routes.dominated(g)
    assert d.routes == frozenset({"b@2"})
    assert d.statements == frozenset({"y", "z"})


def test_proving_the_extra_work_offers_the_route_again() -> None:
    """Nothing is recorded: once ``t--h2--h1`` and ``t--h2--h2`` are proved, ``t--h2@2`` needs
    no more than ``t--h2@1`` (a tie), so the next read offers it again."""
    g = strictly_more()
    assert routes.dominated(g).routes == frozenset({"t--h2@2"})
    for n in g["nodes"]:
        if n["node_id"] in ("t--h2--h1", "t--h2--h2"):
            n["status"] = "proved"
    assert routes.dominated(g).routes == frozenset()
    assert len(routes.read(g).sets) == 2


def test_a_new_route_elsewhere_offers_it_again() -> None:
    """``b@2`` is dominated only because the root needs ``x`` through ``a`` anyway. A new route
    of ``a`` that does not need ``x`` (a merged partial, read at the next render) makes
    ``{w, y, z}`` a way that needs no ``x``, so ``b@2`` is offered again."""
    before = doc(
        node("t", deps=["a", "b"], decompositions=[["a", "b"]]),
        node("a", deps=["x"], decompositions=[["x"]]),
        node("b", deps=["x", "y", "z"], decompositions=[["x"], ["y", "z"]]),
        node("x"),
        node("y"),
        node("z"),
    )
    assert routes.dominated(before).routes == frozenset({"b@2"})
    g = doc(
        node("t", deps=["a", "b"], decompositions=[["a", "b"]]),
        node("a", deps=["x", "w"], decompositions=[["x"], ["w"]]),
        node("b", deps=["x", "y", "z"], decompositions=[["x"], ["y", "z"]]),
        node("x"),
        node("y"),
        node("z"),
        hole("w"),
    )
    assert routes.dominated(g).routes == frozenset()
    assert ["w", "y", "z"] in open_sets(routes.read(g))


def test_sets_that_need_different_statements_are_both_offered() -> None:
    g = doc(
        node("t", deps=["a", "b", "c"], decompositions=[["a", "b"], ["c"]]),
        hole("a"),
        hole("b"),
        hole("c"),
    )
    assert open_sets(routes.read(g)) == [["a", "b"], ["c"]]
    d = routes.dominated(g)
    assert d.routes == frozenset() and d.statements == frozenset()


def test_equal_needs_offer_both_routes() -> None:
    """Two routes of the root through the same hole need the same statements: equal is not
    harder, so neither route is dominated, although the two make one set."""
    g = doc(node("t", deps=["a"], decompositions=[["a"], ["a"]]), hole("a"))
    assert open_sets(routes.read(g)) == [["a"]]
    assert routes.dominated(g).routes == frozenset()


def test_an_extra_assembly_is_not_harder() -> None:
    """``t@2`` reaches the same open leaf through ``m``; ``m`` closes itself once ``a`` is proved
    (D-12 v3.42), so the two routes need the same and both are offered."""
    g = doc(
        node("t", deps=["a", "m"], decompositions=[["a"], ["m"]]),
        hole("a"),
        hole("m", deps=["a"], decompositions=[["a"]]),
    )
    result = routes.read(g)
    assert [(list(s.open), list(s.assemblies)) for s in result.sets] == [
        (["a"], ["t"]),
        (["a"], ["t", "m"]),
    ]
    d = routes.dominated(g)
    assert d.routes == frozenset() and d.statements == frozenset()


def test_a_statement_a_live_proof_rests_on_is_not_dominated() -> None:
    """``q`` is a proved member only of the dominated set, but the proof of ``a``, a proved
    member of the offered set, used it: a kernel-checked fact a live proof uses stays live."""
    g = doc(
        node("t", deps=["a", "b"], decompositions=[["a"], ["a", "b"]]),
        hole("a", "proved", proofs=[["q"]]),
        hole("b", deps=["q", "y"], decompositions=[["q", "y"]]),
        node("q", "proved", proofs=[[]]),
        node("y"),
    )
    d = routes.dominated(g)
    assert d.routes == frozenset({"t@2", "b@1"})
    assert d.statements == frozenset({"b", "y"})


def test_a_proved_statement_only_a_dominated_route_reaches_is_dominated() -> None:
    g = doc(
        node("t", deps=["a", "b", "x"], decompositions=[["a"], ["a", "b", "x"]]),
        hole("a"),
        hole("b", "proved", proofs=[["c"]]),
        node("c", "proved", proofs=[[]]),
        hole("x"),
    )
    d = routes.dominated(g)
    assert d.statements == frozenset({"b", "c", "x"})
    assert d.proved == frozenset({"b", "c"})


def test_a_capped_enumeration_leaves_out_nothing() -> None:
    g = strictly_more()
    d = routes.dominated(g, max_sets=1)
    assert d.truncated is True
    assert d.routes == frozenset() and d.statements == frozenset()


def test_the_coarser_cuts_are_unchanged() -> None:
    """``cut: any`` already lists the minimal sets alone (R6); v3.52 changes the finest."""
    g = strictly_more()
    assert ["t--h1", "t--h2--h1", "t--h2--h2"] not in open_sets(routes.read(g, cut="any"))


# --- erdos-1094 of 2026-11-24 -------------------------------------------------------------------

R = "erdos-1094"
DOMINATED_PREFIXES = (
    f"{R}--h3--h1",  # the residue sieve
    f"{R}--h3--h2",  # Erdős-Lacampagne-Selfridge
    f"{R}--h3--h3",  # Granville-Ramaré, down to Wiener-Ikehara
    f"{R}--h2--h1--h1--h1",  # the n/gcd(n, k) split
    f"{R}--h2--h1--h4--h1",  # the thin strip above k², split by gcd(n, k)
)


@pytest.fixture(scope="module")
def e1094() -> dict[str, Any]:
    found: dict[str, Any] = json.loads(
        (FIXTURES / "erdos-1094-20261124.json").read_text(encoding="utf-8")
    )
    return found


def test_erdos_1094_offers_two_ways_in_four_sets(e1094: dict[str, Any]) -> None:
    """Two choices of open statements, each reached twice: ``--h2--h1@2`` (the strip, whose
    second route goes back through ``--h2--h1--h1``) ties with ``--h2--h1@1``, so both are
    offered. 46 sets before v3.52."""
    result = routes.read(e1094)
    assert result.truncated is False
    assert len(result.sets) == 4
    assert sorted({tuple(o) for o in open_sets(result)}) == sorted(
        [
            (f"{R}--h2--h2--h1--h1", f"{R}--h2--h2--h3--h1--h1--h1--h1"),
            (f"{R}--h2--h2--h1--h1", f"{R}--h2--h2--h5--h2--h2"),
        ]
    )


def test_erdos_1094_dominated_statements_are_the_five_subtrees(e1094: dict[str, Any]) -> None:
    d = routes.dominated(e1094)
    ids = [str(n["node_id"]) for n in e1094["nodes"]]
    expected = {i for i in ids if i.startswith(DOMINATED_PREFIXES)}
    assert d.statements == expected
    status = {str(n["node_id"]): n["status"] for n in e1094["nodes"]}
    assert d.proved == {i for i in expected if status[i] == "proved"}
    assert len(expected) == 60 and len(d.proved) == 9


def test_erdos_1094_dominated_routes(e1094: dict[str, Any]) -> None:
    d = routes.dominated(e1094)
    assert {f"{R}--h3@1", f"{R}--h3@3", f"{R}--h2--h1--h1@1", f"{R}--h2--h1--h4@1"} <= d.routes
    offered = {
        f"{R}@1",
        f"{R}--h2@1",
        f"{R}--h2--h1@1",
        f"{R}--h2--h1@2",  # ties with @1: the strip's second route reaches the same leaves
        f"{R}--h2--h1--h4@2",
        f"{R}--h2--h1--h1@2",
        f"{R}--h3@2",
        f"{R}--h2--h2@1",
        f"{R}--h2--h2@2",
        f"{R}--h2--h2--h1@1",
        f"{R}--h2--h2--h4@1",
        f"{R}--h2--h2--h5@1",
    }
    assert not (offered & d.routes)
    # every dominated route belongs to a node in a dominated subtree or is one of the two
    # alternatives the live nodes give up
    for r in d.routes:
        holder = r.split("@")[0]
        assert holder.startswith(DOMINATED_PREFIXES) or r in {
            f"{R}--h3@1",
            f"{R}--h3@3",
            f"{R}--h2--h1--h1@1",
            f"{R}--h2--h1--h4@1",
        }, r


# --- the frontier -------------------------------------------------------------------------------

H1 = f"{T}--h1"
H3 = f"{T}--h3"


@pytest.fixture(scope="module")
def keys(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    return make_keys(tmp_path_factory.mktemp("dominated-keys"))


def test_the_frontier_omits_a_dominated_statement(tmp_path: Path, keys: dict[str, Path]) -> None:
    """``T`` (open, a dependency of the root; ``A`` is proved in the fixture, so its routes are
    history) gets a second route that restates its first route's hole as a lemma and adds
    ``T--h3``: the same work and more. ``T--h3`` leaves the frontier; ``T--h1`` stays."""
    t = Tree(tmp_path, keys)
    # a partial's holder has no proof of its own; the fixture's T does, and a merged partial's
    # attestation beside a Proof.lean reads as a proof (F03-Q7)
    (t.root / "targets" / TARGET / "nodes" / T / "Proof.lean").unlink()
    t.hole(H1, "h1", parent=T)
    t.partial(T, ["h1"], path="attempts/20261020T000000Z-alice-partial.lean")
    before = t.frontier(t.render())
    assert H1 in before
    t.hole(H3, "h3", parent=T)
    t.lemmas(T, [{"hole": "h1s", "node": H1}])
    t.partial(T, ["h3", "h1s"], path="attempts/20261021T000000Z-bob-partial.lean")
    prod = t.render()
    rows = t.rows(prod)
    assert rows[H3]["status"] == "ready"
    after = t.frontier(prod)
    assert H3 not in after
    assert after == before
    assert ROOT in rows and A in rows
    assert products.PROTOCOL_VERSION == "3.52"
