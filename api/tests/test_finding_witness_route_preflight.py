# ruff: noqa: RUF001 — the fixtures are PR #168's Lean source, with its double-struck letters
"""F13-T21: ``POST /proposals/witness`` pre-flights the witness before it opens a pull request.

The owner's principle (2026-09-24): "we shouldn't get a pull request at all in these cases — it
should be an error sent back to the user, like reusing theorems, not compiling etc." F13-T16 and
T17 put the witness pre-flight on ``POST /proposals/variant`` and ``/proposals/speculative``; the
route that fills a hole's witness slot still opened its pull request on one check, ``"sorry" in
witness``, so a witness of the wrong type, or one that does not compile, became a pull request
the gate's step 7 then refused a queue slot later. The same substring test also refused a real
witness whose *comment* says "sorry" (the slot's own header does), the heuristic the 2026-09-10
sweep named.

Now the route runs ``checks.preflight_witness`` over the hole's committed statement, its
committed Context and the witness, refuses ``422 witness-type-mismatch`` and ``422 witness-fails``
as the proposal routes do, and carries ``witness_preflight`` in its receipt. A checker that
cannot answer still lets the pull request open (``unavailable``, ``inconclusive``): step 7 is the
authority, and whether to fail closed is the owner's call (the audit, task-21-audit.md).
"""

from __future__ import annotations

import json
from typing import Any

from api_fakes import Harness
from mcp_client import TARGET, McpClient
from test_finding_witness_preflight import (
    EXPECTED,
    GIVEN,
    RIGHT,
    STATEMENT,
    WRONG,
    answer,
    harness,
    token,
)
from test_finding_witness_preflight_okay import DECIDE_ERROR, fails

from opn_api.axle import AxleError

HOLE = "and-reassoc--h1"
HOLE_DIR = f"targets/{TARGET}/nodes/{HOLE}/"
GRAPH_PATH = f"targets/{TARGET}/graph.json"
#: A hole's statement as the post-merge writer leaves it: importing its own Context (F07-T23).
HOLE_STATEMENT = f"import Nodes.«{HOLE}».Context\n" + STATEMENT
HOLE_CONTEXT = "-- dependencies: none\ntheorem Opn.hole_context_marker : True := trivial\n"

MISMATCH = answer({"expected": EXPECTED, "given": GIVEN, "matches": False})
MATCH = answer({"expected": EXPECTED, "given": EXPECTED, "matches": True})


def with_hole(h: Harness) -> Harness:
    """The fixture graph with a compiler-derived hole blocked ``witness-missing``, its statement
    and its Context committed, as the post-merge job leaves one (F07-R6)."""
    files = h.githost.files
    doc = json.loads(files[GRAPH_PATH])
    doc["nodes"] = [n for n in doc["nodes"] if n["node_id"] != HOLE]
    doc["nodes"].append(
        {
            "node_id": HOLE,
            "status": "blocked",
            "cause": "witness-missing",
            "deps": [],
            "origin": "compiler-derived",
            "statement_hash": "1" * 64,
            "relation": None,
            "tutorial": False,
            "trust_base": None,
            "proof_commit": None,
        }
    )
    files[GRAPH_PATH] = json.dumps(doc).encode()
    files[HOLE_DIR + "Statement.lean"] = HOLE_STATEMENT.encode()
    files[HOLE_DIR + "Context.lean"] = HOLE_CONTEXT.encode()
    h.context.files.clear()
    return h


def propose(h: Harness, witness: str) -> Any:
    return h.client.post(
        "/proposals/witness",
        json={"node_id": HOLE, "witness": witness},
        headers=h.auth(token(h)),
    )


def test_a_witness_of_the_wrong_type_opens_no_pull_request() -> None:
    h = with_hole(harness(MISMATCH))
    r = propose(h, WRONG)
    assert r.status_code == 422, r.text
    doc = r.json()
    assert doc["error"] == "witness-type-mismatch"
    assert (doc["details"]["expected"], doc["details"]["given"]) == (EXPECTED, GIVEN)
    assert h.githost.pushes == [] and h.githost.pulls == []


def test_a_right_typed_witness_that_does_not_compile_opens_no_pull_request() -> None:
    h = with_hole(harness(fails()))
    r = propose(h, RIGHT)
    assert r.status_code == 422, r.text
    assert r.json()["error"] == "witness-fails"
    assert r.json()["details"]["errors"] == [DECIDE_ERROR]
    assert h.githost.pushes == [] and h.githost.pulls == []


def test_a_matching_witness_opens_and_the_receipt_says_it_was_checked() -> None:
    h = with_hole(harness(MATCH))
    r = propose(h, RIGHT)
    assert r.status_code == 201, r.text
    assert r.json()["witness_preflight"] == "matched"
    assert len(h.githost.pulls) == 1
    (sent,) = h.axle.calls
    # What was checked is the hole's committed statement, its committed Context inlined in place
    # of the import (a module the checker cannot have), and the witness being pushed.
    assert "import Nodes." not in sent.content
    assert "Opn.hole_context_marker" in sent.content
    assert "getConstInfo `Opn.erdos_402_minFac" in sent.content
    assert "theorem witness : ∃ (A : Finset ℕ) (x : ℕ)" in sent.content
    # And what was pushed is the witness alone, byte for byte (F08-R5).
    assert dict(h.githost.pushes[-1].files) == {HOLE_DIR + "Witness.lean": RIGHT}


def test_a_checker_that_cannot_answer_lets_the_witness_proceed_as_before() -> None:
    for reply, word in (
        (AxleError("AXLE check returned 502", status=502), "unavailable"),
        (answer(None, okay=False), "inconclusive"),
    ):
        h = with_hole(harness(reply))
        r = propose(h, WRONG)
        assert r.status_code == 201, r.text
        assert r.json()["witness_preflight"] == word
        assert len(h.githost.pulls) == 1
    h = with_hole(harness(sha="f" * 40))  # a pin the mapping has no entry for
    r = propose(h, WRONG)
    assert r.status_code == 201, r.text
    assert r.json()["witness_preflight"] == "unavailable"
    assert h.axle.calls == []


def test_a_second_witness_for_the_hole_spends_no_check() -> None:
    """F07-T35's copy rule stays first: a hole has one slot, and a refusal is free."""
    h = with_hole(harness(MATCH))
    assert propose(h, RIGHT).status_code == 201
    r = propose(h, RIGHT)
    assert r.status_code == 409, r.text
    assert len(h.axle.calls) == 1


def test_a_comment_naming_sorry_is_not_a_sorry() -> None:
    """The gate's reading (``layout.mentions_sorry``), not a substring: the slot's own header
    comment names the word, and a witness pasted under it is real."""
    h = with_hole(harness(MATCH))
    r = propose(h, "-- this fills the sorry slot\n" + RIGHT)
    assert r.status_code == 201, r.text
    assert r.json()["witness_preflight"] == "matched"


def test_a_sorry_token_is_still_refused_before_any_check() -> None:
    h = with_hole(harness(MATCH))
    r = propose(h, "theorem witness : True := by\n  sorry\n")
    assert (r.status_code, r.json()["error"]) == (400, "witness-invalid"), r.text
    assert h.axle.calls == [] and h.githost.pulls == []


def test_a_proposals_sorry_witness_is_refused_before_any_check() -> None:
    """The same rule on the proposal routes: a ``sorry`` elaborates on the checker (a warning,
    ``okay: true``) and so pre-flighted ``matched``, then failed step 7 as ``witness-sorry``. The
    only witness a node may carry unfilled is the post-merge writer's slot, which no proposal is
    (F08-R14)."""
    from test_finding_witness_preflight import speculative, variant  # noqa: PLC0415

    stub = "theorem witness : True := by\n  sorry\n"
    for route in (variant, speculative):
        h = harness(MATCH)
        r = route(h, stub)
        assert (r.status_code, r.json()["error"]) == (400, "witness-invalid"), r.text
        assert h.axle.calls == [] and h.githost.pulls == []
    h = harness(MATCH)
    assert variant(h, "-- no sorry here\n" + RIGHT).status_code == 201


def test_mcp_propose_witness_carries_the_same_refusal() -> None:
    h = with_hole(harness(fails()))
    bearer = token(h)
    with h.client:
        out = McpClient(h).failed(
            "propose_witness", {"node_id": HOLE, "witness": RIGHT}, token=bearer
        )
    assert out["status"] == 422 and out["body"]["error"] == "witness-fails"
    assert h.githost.pulls == []


def test_a_hole_with_a_proved_record_is_checked_against_the_narrowed_type() -> None:
    """F07-T44 meets F13-T21: a hole whose assembly proved some of its binders carries
    ``proved_binders`` in its committed ``META.yaml``, and step 7 then accepts the narrowed type
    (or the full one). The route's pre-flight must ask the same question, or it would refuse,
    before any pull request, a witness the gate accepts."""
    h = with_hole(harness(MATCH))
    h.githost.files[HOLE_DIR + "META.yaml"] = b"id: and-reassoc--h1\nproved_binders: [1]\n"
    r = propose(h, RIGHT)
    assert r.status_code == 201, r.text
    (sent,) = h.axle.calls
    assert "expectedWitnessTypeNarrowed s.type #[1]" in sent.content
    # The META is read, never pushed: the pull request still carries the witness alone.
    assert dict(h.githost.pushes[-1].files) == {HOLE_DIR + "Witness.lean": RIGHT}
