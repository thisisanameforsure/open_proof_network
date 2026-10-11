"""F13-T32: ``/check`` drops Mathlib's naming-linter warning on every gate-generated hole name it
inlines, not only on the node's own (testers 2026-10-08, erdos-1094).

The guide says the naming linter's warning about the ``__`` in "theorem names the gate generates
for holes" is removed and listed in ``dropped_warnings``. F13-T18 (ruling D6) dropped it only
when the flagged name was the checked node's own declaration. But the fast check inlines the
node's ``Context.lean`` (F13-T12), and after a skeleton merges that file declares the node's
holes under their gate-written names (live: ``erdos_1094__h1``, ``erdos_1094__h2``,
``erdos_1094__h3`` in ``targets/erdos-1094/nodes/erdos-1094/Context.lean``). The linter flags
each of them on every check of the parent, and the contributor can rename none of them.

The rule now: a ``linter.style.nameCheck`` warning is dropped when the name it flags is the
node's own gate-generated declaration (T18), or is declared by a node module the service
inlined (a Context, a used node's statement) *and* is a hole of the target's graph with ``-``
made ``_`` (``postmerge.child_statement``; a D-8 revision of a hole keeps its superseded
hole's name, which is a hole of the graph too). Every other warning stays: a contributor's own
``foo__bar``, a ``__`` name an author gave a dependency, and a hole's name the contributor wrote
into their own text rather than had inlined.
"""

from __future__ import annotations

import json
from typing import Any

from api_fakes import AXLE_OKAY, FakeAxle, Harness
from mcp_client import NODE, NODE_DIR, TARGET
from test_checks import harness_with, post, seed
from test_finding_check_naming_noise import name_check

GRAPH_PATH = f"targets/{TARGET}/graph.json"
OWN = f"import Nodes.«{NODE}».Context"
HOLES = [f"{NODE}--h1", f"{NODE}--h2"]
H1, H2 = (hole.replace("-", "_") for hole in HOLES)
STATEMENT = f"{OWN}\n\ntheorem OpnProp.and_reassoc : True := by\n  sorry\n"
PROOF = f"{OWN}\n\ntheorem OpnProp.and_reassoc : True := by\n  exact {H1}\n"
#: The parent's Context as the post-merge job leaves it once a skeleton's holes are nodes.
CONTEXT = "".join(
    f"/-! Hole `h{i}` of a merged partial proof, as a node (D-12 #5, D-29). -/\n\n"
    f"theorem {name} : True := by\n  sorry\n\n"
    for i, name in enumerate((H1, H2), start=1)
)
MINE = name_check("my__lemma", at="-:12:8-12:17")


def hole_row(node_id: str, origin: str = "compiler-derived") -> dict[str, Any]:
    return {
        "node_id": node_id,
        "status": "blocked",
        "cause": "witness-missing",
        "deps": [],
        "origin": origin,
        "statement_hash": "1" * 64,
        "relation": None,
        "tutorial": False,
        "trust_base": None,
        "proof_commit": None,
    }


def with_holes(
    h: Harness, context: str = CONTEXT, rows: list[dict[str, Any]] | None = None
) -> Harness:
    """The fixture node with its holes on the graph and declared in its committed Context."""
    seed(h, statement=STATEMENT)
    files = h.githost.files
    doc = json.loads(files[GRAPH_PATH])
    added = rows if rows is not None else [hole_row(hole) for hole in HOLES]
    doc["nodes"] = [n for n in doc["nodes"] if n["node_id"] not in {r["node_id"] for r in added}]
    doc["nodes"].extend(added)
    files[GRAPH_PATH] = json.dumps(doc).encode()
    files[NODE_DIR + "Context.lean"] = context.encode()
    h.context.files.clear()
    return h


def reply(*warnings: str) -> dict[str, Any]:
    return {**AXLE_OKAY, "lean_messages": {"errors": [], "warnings": list(warnings), "infos": []}}


def check(
    h: Harness, content: str = PROOF, mode: str = "check", node: str | None = NODE
) -> dict[str, Any]:
    body: dict[str, Any] = {"target_id": TARGET, "content": content, "mode": mode}
    if node is not None:
        body["node_id"] = node
    r = post(h, body)
    assert r.status_code == 200, r.text
    doc: dict[str, Any] = r.json()
    return doc


def harness(*warnings: str) -> Harness:
    return harness_with(axle=FakeAxle(replies=[reply(*warnings)]))


def dropped(*names: str) -> list[dict[str, str]]:
    return [{"linter": "linter.style.nameCheck", "declaration": name} for name in names]


def test_the_holes_the_inlined_context_declares_are_dropped() -> None:
    """The finding: a check of the parent, its Context inlined, warns about each hole's name."""
    h = with_holes(harness(name_check(H1, "-:3:8-3:20"), name_check(H2, "-:7:8-7:20")))
    doc = check(h)
    assert doc["inlined_defs"] == [f"Nodes.«{NODE}».Context"]  # the Context was inlined
    assert doc["result"]["lean_messages"]["warnings"] == []
    assert doc["dropped_warnings"] == dropped(H1, H2)


def test_in_verify_mode_too() -> None:
    h = with_holes(harness(name_check(H1, "-:3:8-3:20")))
    doc = check(h, mode="verify")
    assert doc["result"]["lean_messages"]["warnings"] == []
    assert doc["dropped_warnings"] == dropped(H1)


def test_a_revised_hole_keeps_its_superseded_holes_name() -> None:
    """D-8: ``erdos-69--h2-v2`` declares ``erdos_69__h2``, the name of the hole it supersedes,
    which stays on the graph (live, 2026-10-08). That name is still the gate's."""
    rows = [hole_row(HOLES[0]), hole_row(f"{HOLES[0]}-v2", origin="skeleton-hole")]
    context = f"theorem {H1} : True := by\n  sorry\n"
    h = with_holes(harness(name_check(H1)), context=context, rows=rows)
    doc = check(h)
    assert doc["dropped_warnings"] == dropped(H1)


def test_a_contributors_own_double_underscore_name_still_warns() -> None:
    h = with_holes(harness(name_check(H1, "-:3:8-3:20"), MINE))
    doc = check(h)
    assert doc["result"]["lean_messages"]["warnings"] == [MINE]
    assert doc["dropped_warnings"] == dropped(H1)


def test_an_authored_dependencys_double_underscore_name_still_warns() -> None:
    """A ``__`` name an author gave a node is not the gate's: a Context restating it inlines
    it, but no hole of the graph has that name, so the warning stays (D6: the gate's only)."""
    authored = name_check("OpnProp.dep__lemma")
    context = CONTEXT + "theorem OpnProp.dep__lemma : True := by\n  sorry\n"
    h = with_holes(harness(authored), context=context)
    doc = check(h)
    assert doc["result"]["lean_messages"]["warnings"] == [authored]
    assert doc["dropped_warnings"] == []


def test_a_hole_name_inlined_from_a_context_but_not_on_the_graph_still_warns() -> None:
    """The name's shape alone does not make it the gate's: the graph must carry such a hole."""
    h = with_holes(harness(name_check(H2)), rows=[hole_row(HOLES[0])])
    doc = check(h)
    assert doc["result"]["lean_messages"]["warnings"] == [name_check(H2)]
    assert doc["dropped_warnings"] == []


def test_a_hole_name_the_contributor_wrote_rather_than_had_inlined_still_warns() -> None:
    """A check with no Context inlined (no node named) that declares a hole's name itself: the
    text is the contributor's, so the warning is theirs to act on."""
    own_text = f"theorem {H1} : True := trivial\n"
    h = with_holes(harness(name_check(H1)))
    doc = check(h, content=own_text, node=None)
    assert doc["inlined_defs"] == []
    assert doc["result"]["lean_messages"]["warnings"] == [name_check(H1)]
    assert doc["dropped_warnings"] == []
