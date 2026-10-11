"""F13-T25 (bugs.md item 12, 2026-09-30): ``POST /check`` in ``verify`` mode answered
``okay: true`` for texts the gate would refuse.

``okay`` is read as "the gate would accept this" (the guide's snippet reads nothing else), but
it was the hosted checker's verdict alone, and the checker substitutes its own header, elaborates
``admit`` as ``sorry`` without complaint, and knows nothing of the gate's rules. So a proof using
``admit`` (step 5 refuses ``sorryAx``), a header the gate's proof-is-statement rule refuses at
step 2 (``set_option … in``, an extra ``open``), an alpha-renamed binder in the signature, and —
with no ``node_id`` — an import of a node the graph does not have, all answered ``okay: true``.

The rules. The lint names each case with its own code — ``admit-present``, ``header-diverges``,
``signature-diverges`` (both from the gate's own ``paths.check_proof_is_statement``, not a
re-implementation), ``import-unknown-node`` — and one more keyed on the checker's own words,
``sorry-reported`` (Lean's "declaration uses `sorry`", which a search tactic that found nothing
also leaves behind, since ``apply?`` admits the goal). In verify mode ``okay`` is false with any
finding the gate refuses on, whatever the checker said; an unknown node import is false in every
mode, because the checker never saw the import. What is left alone, probed at Lean 4.33.1
(``engineering/evidence/F13/task-25.txt``): ``exact?``, ``apply?`` and ``simp?`` that succeed
close their goals with no ``sorryAx``, which the gate accepts.
"""

from __future__ import annotations

from typing import Any

from api_fakes import AXLE_OKAY, FakeAxle, Harness
from mcp_client import NODE, STATEMENT, TARGET
from test_checks import PROOF, harness_with, post, seed

from opn_api import checks

OWN = f"import Nodes.«{NODE}».Context"
BOUND = "theorem OpnProp.and_reassoc : ∀ n : Nat, n = n := by\n  sorry\n"


def verify(
    content: str, *, statement: str | None = None, reply: dict[str, Any] | None = None
) -> tuple[Harness, dict[str, Any]]:
    h = harness_with(axle=FakeAxle(replies=[reply or AXLE_OKAY]))
    seed(h, statement=statement or STATEMENT)
    r = post(h, {"target_id": TARGET, "node_id": NODE, "mode": "verify", "content": content})
    assert r.status_code == 200, r.text
    return h, r.json()


def codes(doc: dict[str, Any]) -> list[str]:
    return [w["code"] for w in doc["lint"]]


def test_a_clean_proof_is_okay_with_nothing_to_say() -> None:
    _, doc = verify(PROOF)
    assert doc["okay"] is True and doc["lint"] == []


# --- (i) admit is sorry by another name ----------------------------------------------------------


def test_admit_is_refused_as_the_gate_refuses_sorry() -> None:
    h, doc = verify("theorem OpnProp.and_reassoc : True := by\n  admit\n")
    assert "admit-present" in codes(doc), doc["lint"]
    assert doc["okay"] is False
    assert doc["result"]["okay"] is True  # the checker's own word, still verbatim (R5)
    assert h.store.checks[doc["log_id"]].lint == ["admit-present"]


def test_an_admit_in_a_comment_or_a_name_is_not_one() -> None:
    _, doc = verify(
        "-- admit nothing\ntheorem OpnProp.and_reassoc : True := by\n  exact admitted\n"
    )
    assert "admit-present" not in codes(doc)


def test_sorry_in_verify_mode_is_a_refusal_not_a_warning() -> None:
    _, doc = verify("theorem OpnProp.and_reassoc : True := by\n  sorry\n")
    assert "sorry-present" in codes(doc)
    assert doc["okay"] is False


# --- (ii) a search tactic that found nothing admits the goal; the checker says so ----------------


def test_the_checkers_sorry_warning_is_a_refusal_in_verify_mode() -> None:
    reply = {
        **AXLE_OKAY,
        "lean_messages": {
            "errors": [],
            "warnings": ["-:1:8-1:27: warning: declaration uses `sorry`"],
            "infos": [],
        },
    }
    _, doc = verify("theorem OpnProp.and_reassoc : True := by\n  apply?\n", reply=reply)
    assert "sorry-reported" in codes(doc)
    assert doc["okay"] is False


def test_a_successful_search_tactic_is_left_alone() -> None:
    """Probed at 4.33.1: exact?, apply? and simp? that succeed close the goal with no sorryAx."""
    for tactic in ("exact?", "apply?", "simp?"):
        _, doc = verify(f"theorem OpnProp.and_reassoc : True := by\n  {tactic}\n")
        assert doc["okay"] is True and doc["lint"] == [], (tactic, doc["lint"])


def test_the_checkers_sorry_warning_is_a_warning_in_check_mode() -> None:
    reply = {
        **AXLE_OKAY,
        "lean_messages": {"errors": [], "warnings": ["declaration uses `sorry`"], "infos": []},
    }
    h = harness_with(axle=FakeAxle(replies=[reply]))
    seed(h)
    r = post(h, {"target_id": TARGET, "node_id": NODE, "content": PROOF})
    assert r.status_code == 200, r.text
    assert r.json()["okay"] is True  # mode check asks whether it compiles; it does


# --- (iii) a header the gate refuses at step 2 ---------------------------------------------------


def test_a_set_option_before_the_theorem_diverges_from_the_statement() -> None:
    _, doc = verify("set_option maxHeartbeats 400000 in\n" + PROOF)
    [found] = [w for w in doc["lint"] if w["code"] == "header-diverges"]
    assert found["line"] == 1
    assert found["got"].startswith("set_option") and found["expected"].startswith("theorem")
    assert doc["okay"] is False


def test_an_extra_open_line_diverges_from_the_statement() -> None:
    _, doc = verify("open Nat\n\n" + PROOF)
    assert "header-diverges" in codes(doc), doc["lint"]
    assert doc["okay"] is False


def test_a_changed_import_is_named_once() -> None:
    """The imports lint already names a changed import line; the gate's rule, which would say
    the same of line 1, does not repeat it — but it does flip the verdict."""
    _, doc = verify("import Mathlib\n\n" + PROOF)
    assert codes(doc) == ["imports-differ"]
    assert doc["okay"] is False


def test_the_own_context_import_the_gate_allows_is_allowed_here() -> None:
    """F00-T10: a statement that predates the own-Context line may be proved with it, exactly
    where the gate puts it; the gate's rule is the one applied, so the same allowance holds."""
    _, doc = verify(OWN + "\n\n" + PROOF)
    assert "header-diverges" not in codes(doc) and "imports-differ" not in codes(doc)
    assert doc["okay"] is True


# --- (iv) an alpha-renamed binder in the signature ----------------------------------------------


def test_a_renamed_binder_diverges_from_the_signature() -> None:
    _, doc = verify(
        "theorem OpnProp.and_reassoc : ∀ m : Nat, m = m := by\n  intro m\n  rfl\n", statement=BOUND
    )
    [found] = [w for w in doc["lint"] if w["code"] == "signature-diverges"]
    assert found["line"] == 1
    assert "∀ n : Nat" in found["expected"] and "∀ m : Nat" in found["got"]
    assert doc["okay"] is False


def test_the_signature_as_written_is_accepted() -> None:
    _, doc = verify(
        "theorem OpnProp.and_reassoc : ∀ n : Nat, n = n := by\n  intro n\n  rfl\n", statement=BOUND
    )
    assert doc["okay"] is True and doc["lint"] == []


# --- (v) an import of a node the graph does not have, with no node named ------------------------


def test_an_import_of_an_unknown_node_is_refused_without_a_node_id() -> None:
    h = harness_with()
    seed(h)
    content = "import Nodes.«no-such-node».Context\n\n" + PROOF
    r = post(h, {"target_id": TARGET, "content": content})
    assert r.status_code == 200, r.text
    doc = r.json()
    [found] = [w for w in doc["lint"] if w["code"] == "import-unknown-node"]
    assert found["modules"] == ["Nodes.«no-such-node».Context"]
    assert doc["okay"] is False
    assert h.axle.calls[-1].content == content  # still forwarded untouched (R4)


def test_an_import_of_a_node_the_graph_has_is_not_unknown() -> None:
    h = harness_with()
    seed(h)
    r = post(h, {"target_id": TARGET, "content": OWN + "\n\n" + PROOF})
    assert r.status_code == 200, r.text
    assert "import-unknown-node" not in codes(r.json())
    assert r.json()["okay"] is True


def test_the_mcp_tool_answers_the_same_verdict() -> None:
    """The tool is the route body for body (D-28), so an agent reads the gate's refusal too."""
    from mcp_client import McpClient  # noqa: PLC0415

    h = harness_with(axle=FakeAxle(replies=[AXLE_OKAY]))
    seed(h)
    doc = McpClient(h).ok(
        "check_lean",
        {
            "target_id": TARGET,
            "node_id": NODE,
            "mode": "verify",
            "content": "theorem OpnProp.and_reassoc : True := by\n  admit\n",
        },
    )
    assert doc["body"]["okay"] is False
    assert "admit-present" in [w["code"] for w in doc["body"]["lint"]]


def test_the_refusing_codes_are_one_named_set() -> None:
    """The set a verify verdict keys off, so a new lint cannot flip it unnoticed."""
    assert {
        "imports-differ",
        "helper-declarations",
        "header-diverges",
        "signature-diverges",
        "sorry-present",
        "admit-present",
        "sorry-reported",
        "import-unknown-node",
    } <= checks.GATE_REFUSALS
