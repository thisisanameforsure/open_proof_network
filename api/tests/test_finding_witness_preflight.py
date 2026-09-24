# ruff: noqa: RUF001 — the fixtures are PR #168's Lean source, with its double-struck letters
"""F13-T16: a witness is checked against a statement's *text*, and a proposal is pre-flighted
before its pull request opens (testers 2026-09-23).

Found on erdos-402 by an outside agent. Its variant (graph PR #168, ``variant-3377fd96``) carried
the witness ``∃ A, 0 ∉ A ∧ ∃ x ∈ A, A.card ≤ x.minFac`` where step 7 holds a witness of that
statement to ``∃ A x, 0 ∉ A ∧ x ∈ A ∧ A.card ≤ x.minFac`` — the binder moved out of the
conjunction. The fast check's witness mode (F13-T14) could have said so in seconds, but it reads
a *merged* node's ``Statement.lean``: with the statement as content and no ``node_id`` it
answered ``400 node-id-required``, and with the pending node's id ``409 node-pending``. So the
mismatch was found by the gate after a full round, and the corrected witness went in as a second
pull request (#171) beside a first that had to be closed.

Two fixes, each asserted here and seen red first (``engineering/evidence/F13/task-16.txt``):
``POST /check`` in witness mode takes the statement's text (and the deps its proposal would
declare), and ``POST /proposals/variant`` and ``/proposals/speculative`` run that same check
before opening anything, refusing a mismatch with both types. The pre-flight is a courtesy: when
the checker cannot answer, the proposal proceeds as before and says so, and step 7 decides.
"""

from __future__ import annotations

import json
from typing import Any

import samples
from api_fakes import AXLE_OKAY, FakeAxle, Harness, make_harness
from mcp_client import TARGET, McpClient
from test_finding_check_timeout import HEADROOM_S, LEAN_TIMEOUT, function_timeout_s

from opn_api import axle, checks
from opn_api.axle import AxleError
from opn_gate import schemas

PIN = "0df444a360eaa60ab8c11dca51a86af692955474"  # gate/mathlib-pins.txt, v4.33.1
NODES = f"targets/{TARGET}/nodes/"
DEP = "and-reassoc"
DEP_STATEMENT = "theorem OpnProp.and_reassoc : True := by\n  sorry\n"

#: PR #168's statement, as the agent sent it: the service adds the own-Context import.
STATEMENT = (
    "import Mathlib\n\n"
    "theorem Opn.erdos_402_minFac :\n"
    "    ∀ (A : Finset ℕ), 0 ∉ A → ∀ x ∈ A, A.card ≤ x.minFac →\n"
    "      ∃ a ∈ A, ∃ b ∈ A, a.gcd b ≤ (a / A.card : ℚ) := by\n"
    "  sorry\n"
)
#: PR #168's witness (wrong) and PR #171's (right), byte for byte.
WRONG = (
    "import Mathlib\n\n"
    "theorem witness : ∃ A : Finset ℕ, 0 ∉ A ∧ ∃ x ∈ A, A.card ≤ x.minFac :=\n"
    "  ⟨{2, 3}, by decide, 3, by simp, by rw [Finset.card_pair (by norm_num)]; norm_num⟩\n"
)
RIGHT = (
    "import Mathlib\n\n"
    "theorem witness : ∃ (A : Finset ℕ) (x : ℕ), 0 ∉ A ∧ x ∈ A ∧ A.card ≤ x.minFac :=\n"
    "  ⟨{2, 3}, 3, by decide, by simp, by rw [Finset.card_pair (by norm_num)]; norm_num⟩\n"
)
RELATION = (
    "import Mathlib\n\ntheorem relation :\n"
    "    (∀ (A : Finset ℕ), 0 ∉ A → A.Nonempty →\n"
    "      ∃ᵉ (a ∈ A) (b ∈ A), a.gcd b ≤ (a / A.card : ℚ)) →\n"
    "    (∀ (A : Finset ℕ), 0 ∉ A → ∀ x ∈ A, A.card ≤ x.minFac →\n"
    "      ∃ a ∈ A, ∃ b ∈ A, a.gcd b ≤ (a / A.card : ℚ)) := by\n"
    "  intro h A hA x hx _\n  exact h A hA ⟨x, hx⟩\n"
)
EXPECTED = "∃ (A : Finset ℕ), ∃ (x : ℕ), 0 ∉ A ∧ x ∈ A ∧ A.card ≤ x.minFac"
GIVEN = "∃ (A : Finset ℕ), 0 ∉ A ∧ ∃ x ∈ A, A.card ≤ x.minFac"


def answer(payload: dict[str, Any] | None, *, okay: bool = True) -> dict[str, Any]:
    """The checker's body when the witness program ran (``payload``) or never did (``None``)."""
    infos = (
        [] if payload is None else [f"-:9:0-9:8: info: {checks.WITNESS_TAG} {json.dumps(payload)}"]
    )
    return {
        **AXLE_OKAY,
        "okay": okay,
        "lean_messages": {"errors": [], "warnings": [], "infos": infos},
    }


MISMATCH = answer({"expected": EXPECTED, "given": GIVEN, "matches": False})
MATCH = answer({"expected": EXPECTED, "given": EXPECTED, "matches": True})


def harness(*replies: Any, sha: str | None = PIN, env: dict[str, str] | None = None) -> Harness:
    """The fixture graph, its target pinned to ``sha``, one dep node with a sorry statement, and
    a checker that answers ``replies`` in order."""
    h = make_harness(env, axle=FakeAxle(replies=list(replies)))
    files = h.githost.files
    files[f"targets/{TARGET}/gate-spec.json"] = schemas.canonical_json(
        samples.gate_spec(mathlib_sha=sha)
    )
    files[f"{NODES}{DEP}/Statement.lean"] = DEP_STATEMENT.encode()
    h.context.files.clear()
    return h


def check(h: Harness, body: dict[str, Any]) -> Any:
    return h.client.post("/check", json={"target_id": TARGET, "mode": "witness", **body})


def token(h: Harness) -> str:
    """One identity per harness: the GitHub flow mints a login once."""
    if not hasattr(h, "alice"):
        h.alice = h.token_for("code_alice", "alice")  # type: ignore[attr-defined]
    return str(h.alice)  # type: ignore[attr-defined]


def variant(h: Harness, witness: str, **extra: Any) -> Any:
    body = {
        "target_id": TARGET,
        "statement": STATEMENT,
        "witness": witness,
        "relation": "partial",
        "relation_proof": RELATION,
        **extra,
    }
    return h.client.post("/proposals/variant", json=body, headers=h.auth(token(h)))


def speculative(h: Harness, witness: str, **extra: Any) -> Any:
    body = {"target_id": TARGET, "statement": STATEMENT, "witness": witness, **extra}
    return h.client.post("/proposals/speculative", json=body, headers=h.auth(token(h)))


# --- POST /check, mode witness, with the statement's text -----------------------------------------


def test_pr_168s_witness_is_checked_against_its_statement_before_it_is_a_node() -> None:
    h = harness(MISMATCH)
    r = check(h, {"statement": STATEMENT, "content": WRONG})
    assert r.status_code == 200, r.text
    assert r.json()["witness"] == {"expected": EXPECTED, "given": GIVEN, "matches": False}
    (sent,) = h.axle.calls
    assert sent.method == "check"
    assert sent.content.startswith("import Mathlib\nimport Lean\n"), sent.content[:60]
    assert sent.content.index("theorem Opn.erdos_402_minFac") < sent.content.index(
        "theorem witness"
    )
    assert "getConstInfo `Opn.erdos_402_minFac" in sent.content  # the statement's own name


def test_without_a_witness_the_statement_alone_gives_the_expected_type() -> None:
    h = harness(answer({"expected": EXPECTED, "given": None, "matches": None}))
    r = check(h, {"statement": STATEMENT})
    assert r.status_code == 200, r.text
    assert r.json()["witness"] == {"expected": EXPECTED, "given": None, "matches": None}
    assert "getConstInfo `witness" not in h.axle.calls[0].content


def test_the_deps_a_proposal_would_declare_are_inlined_as_its_context() -> None:
    """The statement a proposal with deps carries imports its own Context, which the service
    generates from the deps' statements; the check inlines exactly that, once."""
    h = harness(MATCH)
    own = "import Nodes.«spec-00000000».Context\n"  # a caller copying a written statement
    r = check(h, {"statement": own + STATEMENT, "content": RIGHT, "deps": [DEP]})
    assert r.status_code == 200, r.text
    sent = h.axle.calls[0].content
    assert sent.count("theorem OpnProp.and_reassoc") == 1
    assert "import Nodes." not in sent  # a module the checker cannot have


def test_a_statements_defs_import_resolves_against_the_target() -> None:
    h = harness(MATCH)
    h.githost.files[f"targets/{TARGET}/defs/Fact.lean"] = b"def Opn.fact : Nat := 1\n"
    h.context.files.clear()
    r = check(h, {"statement": "import Defs.Fact\n" + STATEMENT, "content": RIGHT})
    assert r.status_code == 200, r.text
    assert r.json()["inlined_defs"] == ["Defs.Fact"]
    assert "def Opn.fact" in h.axle.calls[0].content


def test_a_text_that_is_not_one_sorry_theorem_is_refused_by_name() -> None:
    h = harness()
    for text in ("theorem x : True := trivial\n", STATEMENT + "\n" + DEP_STATEMENT, 7):
        r = check(h, {"statement": text, "content": RIGHT})
        assert r.status_code == 400, r.text
        assert r.json()["error"] == "statement-invalid", r.text
    assert h.axle.calls == []


def test_the_statement_field_is_for_witness_mode_without_a_node() -> None:
    h = harness()
    r = check(h, {"statement": STATEMENT, "node_id": DEP})
    assert (r.status_code, r.json()["error"]) == (400, "statement-with-node"), r.text
    r = check(h, {"statement": STATEMENT, "mode": "check", "content": RIGHT})
    assert (r.status_code, r.json()["error"]) == (400, "statement-not-used"), r.text
    r = check(h, {"node_id": DEP, "deps": [DEP]})
    assert (r.status_code, r.json()["error"]) == (400, "deps-without-statement"), r.text
    r = check(h, {"statement": STATEMENT, "deps": ["no-such-node"]})
    assert (r.status_code, r.json()["error"]) == (404, "dep-unknown"), r.text
    assert h.axle.calls == []


# --- the pre-flight on POST /proposals/variant and /proposals/speculative ------------------------


def test_pr_168s_wrong_witness_opens_no_pull_request() -> None:
    h = harness(MISMATCH)
    r = variant(h, WRONG)
    assert r.status_code == 422, r.text
    doc = r.json()
    assert doc["error"] == "witness-type-mismatch"
    assert (doc["details"]["expected"], doc["details"]["given"]) == (EXPECTED, GIVEN)
    assert h.githost.pushes == [] and h.githost.pulls == []


def test_a_matching_witness_opens_the_pull_request_and_says_it_was_checked() -> None:
    h = harness(MATCH)
    r = variant(h, RIGHT)
    assert r.status_code == 201, r.text
    assert r.json()["witness_preflight"] == "matched"
    assert len(h.githost.pulls) == 1
    (sent,) = h.axle.calls
    # The bytes checked are the bytes pushed: the statement as written, its Context inlined.
    assert "import Nodes." not in sent.content
    assert "getConstInfo `Opn.erdos_402_minFac" in sent.content
    assert "theorem witness : ∃ (A : Finset ℕ) (x : ℕ)" in sent.content


def test_the_speculative_route_checks_with_its_deps_context() -> None:
    h = harness(MISMATCH, MATCH)
    r = speculative(h, WRONG, deps=[DEP])
    assert (r.status_code, r.json()["error"]) == (422, "witness-type-mismatch"), r.text
    assert h.githost.pulls == []
    r = speculative(h, RIGHT, deps=[DEP])
    assert r.status_code == 201, r.text
    assert r.json()["witness_preflight"] == "matched"
    assert all(c.content.count("theorem OpnProp.and_reassoc") == 1 for c in h.axle.calls)


def test_a_checker_that_cannot_answer_lets_the_proposal_proceed_as_before() -> None:
    """Down, out of time, or no environment for the pin: step 7 remains the authority."""
    for reply in (AxleError("AXLE check returned 502", status=502), LEAN_TIMEOUT):
        h = harness(reply)
        r = variant(h, WRONG)
        assert r.status_code == 201, r.text
        assert r.json()["witness_preflight"] == "unavailable"
        assert len(h.githost.pulls) == 1
    h = harness(sha="f" * 40)  # a pin the mapping has no entry for
    r = variant(h, WRONG)
    assert r.status_code == 201, r.text
    assert r.json()["witness_preflight"] == "unavailable"
    assert h.axle.calls == []


def test_a_checker_answer_that_names_no_statement_error_is_inconclusive_not_refused() -> None:
    """Restated by F13-T23 (audit Q-a). This pinned "the program did not run, so no verdict" as
    ``inconclusive`` whatever the reason; the owner's principle made a statement that does not
    compile a refusal (``statement-fails``, ``test_finding_preflight_refusals.py``). What it was
    about still holds: an answer that says ``okay: false`` and names no Lean error on the
    statement's lines (none at all, or only past them) is no verdict, and never a refusal."""
    h = harness(answer(None, okay=False))
    r = variant(h, WRONG)
    assert r.status_code == 201, r.text
    assert r.json()["witness_preflight"] == "inconclusive"
    late = answer(None, okay=False)
    late["lean_messages"]["errors"] = ["-:400:0-400:8: error: unknown constant 'witness'"]
    h = harness(late)
    r = variant(h, WRONG)
    assert r.status_code == 201, r.text
    assert r.json()["witness_preflight"] == "inconclusive"


def test_the_pre_flight_is_charged_and_logged_as_a_check() -> None:
    """The check budget bounds it (a spent budget skips it, never refuses the proposal), and the
    call log keeps it without its text, as every call to the checker (R9)."""
    h = harness(MATCH)
    r = variant(h, RIGHT)
    assert r.status_code == 201, r.text
    (record,) = h.store.checks.values()
    assert (record.mode, record.outcome, record.caller_kind) == ("witness", "answered", "identity")
    assert record.node_id == r.json()["node_id"]

    spent = harness(MATCH, env={"OPN_API_CHECKS_PER_HOUR": "1"})
    first = spent.client.post(
        "/check", json={"target_id": TARGET, "content": RIGHT}, headers=spent.auth(token(spent))
    )
    assert first.status_code == 200, first.text  # the hour's one check, spent
    r = variant(spent, RIGHT)
    assert r.status_code == 201, r.text
    assert r.json()["witness_preflight"] == "unavailable"
    assert len(spent.axle.calls) == 1  # the check's, and none for the pre-flight


def test_the_pre_flight_leaves_the_function_time_to_open_the_pull_request() -> None:
    """T13's budget, with the pull request's own calls after it (a branch, a commit, a PR)."""
    h = harness(MATCH)
    variant(h, RIGHT)
    budget = h.axle.calls[0].timeout_s
    assert budget == checks.PREFLIGHT_TIMEOUT_S < h.settings.check_timeout_s
    worst = checks.SLOT_WAIT_S + axle.CONNECT_TIMEOUT_S + budget + axle.READ_GRACE_S
    assert worst + checks.PREFLIGHT_PR_HEADROOM_S + HEADROOM_S <= function_timeout_s()


# --- the MCP tools, the same answers ------------------------------------------------------------


def test_check_lean_takes_the_statement_and_its_deps() -> None:
    from opn_api.mcp.server import BY_NAME  # noqa: PLC0415

    props = BY_NAME["check_lean"].input_schema["properties"]
    assert "statement" in props and "deps" in props
    h = harness(MISMATCH)
    with h.client:
        out = McpClient(h).ok(
            "check_lean",
            {"target_id": TARGET, "mode": "witness", "statement": STATEMENT, "content": WRONG},
        )
    assert out["status"] == 200
    assert out["body"]["witness"] == {"expected": EXPECTED, "given": GIVEN, "matches": False}


def test_propose_variant_refuses_the_mismatch_through_the_mcp_too() -> None:
    h = harness(MISMATCH)
    bearer = token(h)
    with h.client:
        out = McpClient(h).failed(
            "propose_variant",
            {
                "target_id": TARGET,
                "stmt": STATEMENT,
                "witness": WRONG,
                "relation": "partial",
                "relation_proof": RELATION,
            },
            token=bearer,
        )
    assert out["status"] == 422 and out["body"]["error"] == "witness-type-mismatch"
    assert out["body"]["details"]["expected"] == EXPECTED
    assert h.githost.pulls == []
