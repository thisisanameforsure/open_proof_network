# ruff: noqa: RUF001 — the fixtures are PR #168's Lean source, with its double-struck letters
"""F13-T17: the witness pre-flight reads the checker's ``okay`` (testers 2026-09-24, finding 2).

Found on erdos-402 by the MCP agent at 12:40:51Z. Its script proposed the |A| = 7 variant (graph
PR #195) with a witness a ``sed`` had mangled to a six-element set, so the witness's ``decide``
proved the statement *false*. One second earlier its own ``check_lean`` in witness mode had
answered ``witness.matches: true`` beside ``okay: false`` and a ``decide`` error, and the
proposal's receipt still said ``witness_preflight: "matched"``. Step 7 refused it one queue slot
later.

Mechanism: ``checks.preflight_witness`` read the program's ``matches`` (the witness's *type*) and
never the body's ``okay``. A declaration whose proof fails still has its stated type, so the
program ran, compared the types, and said they matched.

Ruling D1 (Mike, 2026-09-24): a witness whose type matches but that does not compile is refused
``422 witness-fails``, naming the checker's errors and the call's log id, and nothing is opened.
A body with no ``okay`` (``user_error``) stays ``inconclusive``; a timeout stays ``unavailable``.
"""

from __future__ import annotations

from typing import Any

import pytest
from mcp_client import TARGET, McpClient
from test_finding_check_timeout import LEAN_TIMEOUT
from test_finding_witness_preflight import (
    EXPECTED,
    RELATION,
    RIGHT,
    STATEMENT,
    WRONG,
    answer,
    harness,
    speculative,
    token,
    variant,
)

#: The error the hosted checker gave PR #195's witness (the shape AXLE's lean_messages carry).
DECIDE_ERROR = (
    "-:6:62-6:68: error: decide proved that the proposition\n"
    "  ({1, 2, 3, 4, 5, 7} : Finset ℕ).card = 7\nis false"
)


def fails() -> dict[str, Any]:
    """The body #195's witness got: the program ran, the types matched, the proof did not."""
    body = answer({"expected": EXPECTED, "given": EXPECTED, "matches": True}, okay=False)
    body["lean_messages"] = {**body["lean_messages"], "errors": [DECIDE_ERROR]}
    return body


@pytest.mark.xfail(strict=True, reason="F13-T17: the pre-flight ignores okay")
def test_a_right_typed_witness_that_does_not_compile_is_not_matched() -> None:
    h = harness(fails())
    r = variant(h, RIGHT)
    assert r.status_code == 422, r.text
    assert r.json()["error"] == "witness-fails", r.text
    assert h.githost.pushes == [] and h.githost.pulls == []


@pytest.mark.xfail(strict=True, reason="F13-T17: the pre-flight ignores okay")
def test_the_refusal_names_the_checker_errors_and_the_log_id() -> None:
    h = harness(fails())
    r = variant(h, RIGHT)
    assert r.status_code == 422, r.text
    details = r.json()["details"]
    assert details["errors"] == [DECIDE_ERROR]
    record = h.store.checks[details["log_id"]]
    assert (record.mode, record.outcome, record.okay) == ("witness", "answered", False)


def test_a_timeout_is_still_unavailable_never_a_refusal() -> None:
    h = harness(LEAN_TIMEOUT)
    r = variant(h, RIGHT)
    assert r.status_code == 201, r.text
    assert r.json()["witness_preflight"] == "unavailable"


@pytest.mark.xfail(strict=True, reason="F13-T17: the pre-flight ignores okay")
def test_no_verdict_at_all_stays_inconclusive() -> None:
    """``user_error`` and no ``okay``: the checker said nothing about the witness (D1)."""
    body = answer({"expected": EXPECTED, "given": EXPECTED, "matches": True})
    body.pop("okay")
    body["user_error"] = "the statement did not compile"
    h = harness(body)
    r = variant(h, RIGHT)
    assert r.status_code == 201, r.text
    assert r.json()["witness_preflight"] == "inconclusive"


def test_a_compiling_right_typed_witness_is_still_matched() -> None:
    h = harness(answer({"expected": EXPECTED, "given": EXPECTED, "matches": True}, okay=True))
    r = variant(h, RIGHT)
    assert r.status_code == 201, r.text
    assert r.json()["witness_preflight"] == "matched"


@pytest.mark.xfail(strict=True, reason="F13-T17: the pre-flight ignores okay")
def test_speculative_and_variant_routes_agree() -> None:
    h = harness(fails(), fails())
    a, b = variant(h, RIGHT), speculative(h, RIGHT)
    assert (a.status_code, a.json()["error"]) == (422, "witness-fails"), a.text
    assert (b.status_code, b.json()["error"]) == (422, "witness-fails"), b.text
    assert a.json()["details"]["errors"] == b.json()["details"]["errors"]
    assert h.githost.pulls == []


def test_a_wrong_type_is_still_the_mismatch_whatever_okay_says() -> None:
    """The type is the more specific answer: a mismatch that also fails is refused as one."""
    from test_finding_witness_preflight import GIVEN  # noqa: PLC0415

    h = harness(answer({"expected": EXPECTED, "given": GIVEN, "matches": False}, okay=False))
    r = variant(h, WRONG)
    assert (r.status_code, r.json()["error"]) == (422, "witness-type-mismatch"), r.text


@pytest.mark.xfail(strict=True, reason="F13-T17: the pre-flight ignores okay")
def test_mcp_propose_variant_carries_the_same_refusal() -> None:
    h = harness(fails())
    bearer = token(h)
    with h.client:
        out = McpClient(h).failed(
            "propose_variant",
            {
                "target_id": TARGET,
                "stmt": STATEMENT,
                "witness": RIGHT,
                "relation": "partial",
                "relation_proof": RELATION,
            },
            token=bearer,
        )
    assert out["status"] == 422 and out["body"]["error"] == "witness-fails"
    assert out["body"]["details"]["errors"] == [DECIDE_ERROR]
    assert h.githost.pulls == []
