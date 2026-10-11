"""F13-T30 (audit 2026-10-04; testers 2026-10-01, A15 and A6): two ``POST /check`` verdicts that
disagreed with the gate.

``okay`` is read as "would the gate accept this?" (F13-T25, Q26). Two answers said otherwise.

* A15. ``mode: check`` on a text that still says ``sorry`` answered ``okay: true`` beside
  ``failed_declarations: ["t"]`` and "Declaration 't' is incomplete": the checker compiles a
  ``sorry`` with a warning, and only ``lint: sorry-present`` said what the gate would do (step 5
  refuses ``sorryAx``). The text's own ``sorry`` (or ``admit``) now makes ``okay`` false in check
  mode too. Keyed on the caller's text, never on the checker's "declaration uses sorry", which
  in check mode is as often a node's Context restating a dependency with a ``sorry`` body: the
  guide sends exactly such a proof to ``mode: check``, and that answer stays true.
* A6. ``mode: verify`` on a node whose Context restates a hole answered ``okay: false`` (with
  ``context-restated`` and ``sorry-reported``, ``failed_declarations`` naming the Context's
  theorem) for a direct proof that never named it, which the precheck and the gate then passed
  (graph #335). ``context-restated`` is not a gate refusal. When the checker's only failures are
  declarations other than the proof's own theorem, and Lean reported no error, the failure is the
  restated Context's and the verdict is true, with the lint as the warning it is.
"""

from __future__ import annotations

from typing import Any

from api_fakes import AXLE_OKAY, FakeAxle
from mcp_client import NODE, TARGET
from test_checks import PROOF, harness_with, post, seed

OWN = f"import Nodes.«{NODE}».Context"
STATEMENT = f"{OWN}\n\ntheorem OpnProp.and_reassoc : True := by\n  sorry\n"
OWN_PROOF = f"{OWN}\n\ntheorem OpnProp.and_reassoc : True := by\n  trivial\n"
RESTATING = (
    "/-! Declared dependencies (D-4 step 8): `dep`. -/\n\n"
    "theorem OpnProp.dep : True := by\n  sorry\n"
)
SORRY_WARNING = "-:3:8-3:19: warning: declaration uses `sorry`"


def codes(doc: dict[str, Any]) -> list[str]:
    return [w["code"] for w in doc["lint"]]


# --- A15: mode check and the text's own sorry -----------------------------------------------------


def check(content: str, reply: dict[str, Any]) -> dict[str, Any]:
    h = harness_with(axle=FakeAxle(replies=[reply]))
    seed(h)
    r = post(h, {"target_id": TARGET, "node_id": NODE, "content": content, "mode": "check"})
    assert r.status_code == 200, r.text
    doc: dict[str, Any] = r.json()
    return doc


INCOMPLETE = {
    **AXLE_OKAY,  # the checker's own okay is true: it compiled, with a warning
    "failed_declarations": ["OpnProp.and_reassoc"],
    "lean_messages": {"errors": [], "warnings": [SORRY_WARNING], "infos": []},
}


def test_a_sorry_in_the_text_is_okay_false_in_check_mode() -> None:
    doc = check("theorem OpnProp.and_reassoc : True := by\n  sorry\n", INCOMPLETE)
    assert "sorry-present" in codes(doc)
    assert doc["okay"] is False
    assert doc["result"]["okay"] is True  # the checker's word stays verbatim


def test_an_admit_in_the_text_is_okay_false_in_check_mode() -> None:
    doc = check("theorem OpnProp.and_reassoc : True := by\n  admit\n", INCOMPLETE)
    assert "admit-present" in codes(doc)
    assert doc["okay"] is False


def test_a_contexts_sorry_is_not_the_texts_in_check_mode() -> None:
    """The guide's own case: a proof that uses a dependency restated with a sorry body is
    checked with mode check, and the checker's warning is the Context's, not the proof's."""
    reply = {
        **AXLE_OKAY,
        "lean_messages": {"errors": [], "warnings": [SORRY_WARNING], "infos": []},
    }
    doc = check(PROOF, reply)
    assert doc["okay"] is True and "sorry-present" not in codes(doc)


# --- A6: verify and a restated Context ------------------------------------------------------------


def verify_restated(reply: dict[str, Any], content: str = OWN_PROOF) -> dict[str, Any]:
    h = harness_with(axle=FakeAxle(replies=[reply]))
    seed(h, statement=STATEMENT)
    h.githost.files[f"targets/{TARGET}/nodes/{NODE}/Context.lean"] = RESTATING.encode()
    h.context.files.clear()
    r = post(h, {"target_id": TARGET, "node_id": NODE, "content": content, "mode": "verify"})
    assert r.status_code == 200, r.text
    doc: dict[str, Any] = r.json()
    return doc


def context_failure(*failed: str, errors: tuple[str, ...] = ()) -> dict[str, Any]:
    return {
        **AXLE_OKAY,
        "okay": False,
        "failed_declarations": list(failed),
        "lean_messages": {"errors": list(errors), "warnings": [SORRY_WARNING], "infos": []},
    }


def test_a_failure_of_the_restated_context_alone_is_okay_true_in_verify_mode() -> None:
    doc = verify_restated(context_failure("OpnProp.dep"))
    assert "context-restated" in codes(doc)
    assert "sorry-reported" not in codes(doc)  # the sorry is the Context's, not the proof's
    assert doc["okay"] is True
    assert doc["result"]["okay"] is False  # verbatim


def test_a_failure_of_the_proofs_own_theorem_stays_false() -> None:
    doc = verify_restated(context_failure("OpnProp.dep", "OpnProp.and_reassoc"))
    assert doc["okay"] is False
    assert "sorry-reported" in codes(doc)


def test_a_lean_error_stays_false() -> None:
    doc = verify_restated(context_failure("OpnProp.dep", errors=("unsolved goals",)))
    assert doc["okay"] is False


def test_a_sorry_in_the_proof_itself_stays_false() -> None:
    content = f"{OWN}\n\ntheorem OpnProp.and_reassoc : True := by\n  sorry\n"
    doc = verify_restated(context_failure("OpnProp.dep"), content)
    assert doc["okay"] is False and "sorry-present" in codes(doc)


def test_with_no_restated_context_a_failure_is_the_checkers() -> None:
    """Without context-restated nothing is reattributed: the checker's no stands."""
    h = harness_with(axle=FakeAxle(replies=[context_failure("OpnProp.dep")]))
    seed(h, statement=STATEMENT)
    r = post(h, {"target_id": TARGET, "node_id": NODE, "content": OWN_PROOF, "mode": "verify"})
    assert r.status_code == 200, r.text
    assert r.json()["okay"] is False
