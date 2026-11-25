"""mcpfix WB2 item 6 (testers 2026-11-25, qa-eb L7 and L8): two refusals that named the wrong thing.

* ``POST /tokens`` with a tutorial proof missing ``job_id`` or ``nonce`` answered the generic
  "unknown, unfinished, used or unusable tutorial proof"; a missing field is a fact about the
  request, not about a job, so naming it tells a caller nothing it may not probe.
* ``github-login-required`` always said "can steward a problem or approve words", whatever the
  route; each route now names the act it refused.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from api_fakes import Harness, make_harness
from test_finding_login_before_fields import tutorial_session
from test_web_session import ENV, web_headers

from opn_api import identity

#: Each GitHub-only route and the words of the act its refusal must name.
ACTS = {
    "/stewards": "steward a problem",
    "/approvals": "approve words",
    "/motions": "open a panel motion",
    "/votes": "vote on a panel motion",
    "/writeups": "record a panel write-up",
    "/literature/confirm": "confirm or dispute a literature status",
    "/registrations": "register a target",
    "/shelvings": "shelve a statement or retire a route",
    "/reviews": "open a formalization review",
    "/reviews/erdos-849/answers": "answer a review question",
    "/reviews/erdos-849/signatures": "sign a formalization review",
}


@pytest.fixture
def h() -> Iterator[Harness]:
    harness = make_harness(ENV)
    with harness.client:
        yield harness


@pytest.mark.parametrize(("route", "act"), sorted(ACTS.items()))
def test_github_login_required_names_the_act_refused(h: Harness, route: str, act: str) -> None:
    r = h.client.post(route, json={}, headers=web_headers(tutorial_session(h)))
    assert r.status_code == 403, r.text
    body = r.json()
    assert body["error"] == "github-login-required"
    assert act in body["message"], body["message"]
    assert "can steward a problem or approve words" not in body["message"] or route in (
        "/stewards",
        "/approvals",
    )


def _tokens(h: Harness, proof: dict[str, object]) -> dict[str, object]:
    r = h.client.post(
        "/tokens",
        json={
            "proof": proof,
            "pseudonym": "missing-field",
            "dco": {"version": identity.DCO_VERSION, "accepted": True},
        },
    )
    assert r.status_code == 400, r.text
    doc: dict[str, object] = r.json()
    return doc


@pytest.mark.parametrize("missing", ["job_id", "nonce"])
def test_a_tutorial_proof_missing_a_field_names_it(h: Harness, missing: str) -> None:
    proof: dict[str, object] = {"kind": "tutorial", "job_id": "01M00000000000000000000000"}
    proof["nonce"] = "x"
    del proof[missing]
    body = _tokens(h, proof)
    assert body["error"] == "proof-invalid"
    assert missing in str(body["message"]), body["message"]
    assert "unknown, unfinished, used or unusable" not in str(body["message"])


def test_a_tutorial_proof_with_both_fields_keeps_the_one_refusal(h: Harness) -> None:
    """The job conditions stay one refusal: which one failed is not for an anonymous caller."""
    body = _tokens(h, {"kind": "tutorial", "job_id": "01M00000000000000000000000", "nonce": "x"})
    assert body["message"] == "unknown, unfinished, used or unusable tutorial proof"


@pytest.mark.parametrize("value", ["", "   ", 7])
def test_an_empty_or_non_string_field_is_named_too(h: Harness, value: object) -> None:
    body = _tokens(h, {"kind": "tutorial", "job_id": value, "nonce": "x"})
    assert "job_id" in str(body["message"]), body["message"]
