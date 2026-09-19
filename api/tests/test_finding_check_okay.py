"""F13-T10: the fast check's response always says ``okay``, and says why when it cannot (F13-Q13).

Found by an outside contributor, 2026-09-18. ``POST /check`` passes AXLE's body through verbatim
as ``result`` (R5), and the guide's snippet reads ``answer["result"]["okay"]``. In ``verify`` mode
against a node whose *statement* does not compile, AXLE answers ``{"user_error": ..., "info":
...}`` with no ``okay`` key at all, so the guide's own snippet raises ``KeyError`` on the one
answer a contributor most needs to read. The service already knew the key could be missing (the
call log stores ``okay`` as tri-state) and never told the caller.

``result`` stays verbatim. Beside it the response gains ``okay``: true, false, or null when the
checker gave no verdict, with ``user_error`` carrying its reason. A second shape was seen the
same day and is pinned here as it is: ``okay: false`` with an empty ``failed_declarations``.
"""

from __future__ import annotations

from typing import Any

from api_fakes import AXLE_OKAY, FakeAxle
from mcp_client import NODE, TARGET
from test_checks import PROOF, harness_with, post, seed

NO_VERDICT: dict[str, Any] = {
    "user_error": "failed to compile formal_statement: failed to synthesize HMul Nat Nat Int",
    "info": {"request_id": "req-user-error"},
}
UNSOLVED: dict[str, Any] = {
    **AXLE_OKAY,
    "okay": False,
    "failed_declarations": [],
    "lean_messages": {"errors": ["unsolved goals"], "warnings": [], "infos": []},
}


def answer(reply: dict[str, Any], **body: Any) -> dict[str, Any]:
    h = harness_with(axle=FakeAxle(replies=[reply]))
    seed(h)
    r = post(h, {"target_id": TARGET, "content": PROOF, **body})
    assert r.status_code == 200, r.text
    doc: dict[str, Any] = r.json()
    return doc


def test_a_clean_answer_says_okay_true_beside_the_verbatim_result() -> None:
    doc = answer(AXLE_OKAY)
    assert doc["okay"] is True and doc["user_error"] is None
    assert doc["result"] == AXLE_OKAY


def test_a_statement_that_does_not_compile_says_okay_null_and_why() -> None:
    doc = answer(NO_VERDICT, node_id=NODE, mode="verify")
    assert "okay" not in doc["result"], "guard: the shape the contributor met"
    assert doc["okay"] is None
    assert doc["user_error"] == NO_VERDICT["user_error"]
    assert doc["result"] == NO_VERDICT  # still verbatim (R5)


def test_a_failed_check_says_okay_false_even_with_no_failed_declaration() -> None:
    doc = answer(UNSOLVED)
    assert doc["okay"] is False and doc["user_error"] is None
    assert doc["result"]["failed_declarations"] == []


def test_a_non_boolean_okay_is_no_verdict() -> None:
    doc = answer({**AXLE_OKAY, "okay": "yes"})
    assert doc["okay"] is None


def test_the_record_and_the_response_agree() -> None:
    h = harness_with(axle=FakeAxle(replies=[NO_VERDICT]))
    seed(h)
    alice = h.token_for("code_alice", "alice")
    r = post(
        h, {"target_id": TARGET, "node_id": NODE, "mode": "verify", "content": PROOF}, h.auth(alice)
    )
    doc = r.json()
    record = h.client.get(f"/checks/{doc['log_id']}", headers=h.auth(alice)).json()
    assert record["okay"] is None and doc["okay"] is None
