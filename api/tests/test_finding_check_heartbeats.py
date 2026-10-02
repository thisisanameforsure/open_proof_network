# ruff: noqa: RUF001 — the fixtures are Lean source, with its double-struck letters
"""F13-T27 (testers 2026-10-01, A8; the owner, 2026-10-01: "okay, report heartbeats from the fast
check. If that's even possible, I'm not sure that it is."): how many heartbeats each theorem used.

Ten agents asked. Lean caps one declaration at 200000 heartbeats, helper declarations are refused,
and the fast check said nothing about how close a proof was: three agents found the cap by
bisection, and a proof over it is reported as a timeout at whatever tactic happened to be running.

What is possible, found out before any code (``engineering/evidence/F13/task-27.txt``):

* The hosted checker returns no such figure. Its answers carry ``timings`` (``parse_ms``,
  ``total_ms``) and ``info`` (request and queue times) for the whole text and nothing per
  declaration, in every body seen in ``check`` and ``verify_proof``.
* Mathlib's ``#count_heartbeats in``, placed before a declaration, prints
  ``Used N heartbeats, which is less than the current maximum of 200000.`` as an info message at
  its own line. Probed on the hosted checker (log 01M3WPRQM0BVWQ1HF186KE3EHT): it must come before
  the doc comment (after it: ``unexpected token '#count_heartbeats'; expected 'lemma'``), the
  older spelling ``count_heartbeats in`` is a parse error, and the command runs its declaration
  without the cap, so a count above the cap is printed (``which is greater than the current
  maximum``) where the plain text would stop.

So ``"heartbeats": true`` on ``POST /check`` (modes ``check`` and ``verify``) sends a second,
side-by-side call with a *copy* of the text in which the command stands before each top-level
theorem and lemma of the caller's content, and answers ``heartbeats`` with the parsed counts,
labelled as a measurement by the fast checker. The verdict (``okay``, ``result``, ``lint``) is
still that of the text as it was sent: the copy is never judged.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any

import pytest
from api_fakes import AXLE_OKAY, AxleCall, FakeAxle, Harness
from mcp_client import NODE, TARGET, McpClient
from test_checks import harness_with, post, refused, seed

from opn_api import checks
from opn_api.axle import AxleAnswer, AxleError

COMMAND = "#count_heartbeats in"

#: A proof file as an agent sends it: a header, a doc comment, an attribute, a private lemma, a
#: definition, a theorem named in a comment and in a string.
CONTENT = """import Mathlib

open Nat in
/-- The first one.
theorem not_this_one : in a doc comment -/
theorem Opn.hb_one (n : ℕ) : n + 0 = n := by
  simp

-- theorem commented_out : True := trivial
def Opn.helper : String := "theorem in_a_string : True"

@[simp]
private lemma Opn.hb_two : (2 : ℝ) ^ 10 = 1024 := by
  norm_num

/- a block comment
theorem also_not : True -/
theorem Opn.hb_three : True := by
  have h : True := trivial
  exact h
"""

MEASURED = """import Mathlib

open Nat in
#count_heartbeats in
/-- The first one.
theorem not_this_one : in a doc comment -/
theorem Opn.hb_one (n : ℕ) : n + 0 = n := by
  simp

-- theorem commented_out : True := trivial
def Opn.helper : String := "theorem in_a_string : True"

#count_heartbeats in
@[simp]
private lemma Opn.hb_two : (2 : ℝ) ^ 10 = 1024 := by
  norm_num

/- a block comment
theorem also_not : True -/
#count_heartbeats in
theorem Opn.hb_three : True := by
  have h : True := trivial
  exact h
"""


def used(line: int, last: str, count: int, relation: str = "less", cap: int = 200000) -> str:
    """The checker's own message, as captured on 2026-10-01."""
    return (
        f"-:{line}:0-{last}: info: Used {count} heartbeats, which is {relation} than the "
        f"current maximum of {cap}.\n"
    )


def measured_body(text: str, *counts: tuple[int, str, int]) -> dict[str, Any]:
    """An answer to the measuring call: ``content`` echoes the text checked (the checker's own
    header in place of the imports, which shifts no line here), one info per command."""
    lines = text.splitlines()
    at = [i + 1 for i, line in enumerate(lines) if line == COMMAND]
    infos = [
        used(line, f"{line + 3}:6", count, relation, cap)
        for line, (count, relation, cap) in zip(at, counts, strict=True)
    ]
    return {
        **AXLE_OKAY,
        "content": text,
        "lean_messages": {"errors": [], "warnings": [], "infos": infos},
        "info": {"request_id": "req-measure"},
    }


@dataclass
class MeasuringAxle(FakeAxle):
    """Answers the text that carries the command from ``measures`` and anything else from
    ``replies``: the two calls run side by side, so their order of arrival is not fixed."""

    measures: list[Any] = field(default_factory=list)
    barrier: threading.Barrier | None = None

    def check(self, content: str, *, environment: str, timeout_s: float) -> AxleAnswer:
        if self.barrier is not None:
            self.barrier.wait()
        if COMMAND in content:
            self.calls.append(AxleCall("check", content, environment, timeout_s))
            reply = self.measures.pop(0) if self.measures else AXLE_OKAY
            if isinstance(reply, AxleError):
                raise reply
            if callable(reply):
                reply = reply(content)
            return AxleAnswer(body=reply, request_id="req-measure", latency_ms=1)
        return super().check(content, environment=environment, timeout_s=timeout_s)


def three_counts(text: str) -> dict[str, Any]:
    return measured_body(text, (31, "less", 200000), (63, "less", 200000), (9, "less", 200000))


def harness(*measures: Any, **axle: Any) -> Harness:
    h = harness_with(axle=MeasuringAxle(measures=list(measures or [three_counts]), **axle))
    seed(h)
    return h


def measuring_calls(h: Harness) -> list[AxleCall]:
    return [c for c in h.axle.calls if COMMAND in c.content]


# --- the copy -------------------------------------------------------------------------------------


def test_the_command_goes_before_each_top_level_theorem_and_its_doc_comment() -> None:
    text, names = checks.count_heartbeats_text(CONTENT)
    assert names == ["Opn.hb_one", "Opn.hb_two", "Opn.hb_three"]
    assert text == MEASURED


def test_a_text_that_already_counts_is_not_counted_twice() -> None:
    """An agent who wrote the command by hand keeps its own line; the copy adds none before it."""
    text, names = checks.count_heartbeats_text(MEASURED)
    assert text == MEASURED and names == ["Opn.hb_one", "Opn.hb_two", "Opn.hb_three"]


def test_a_text_with_no_theorem_is_left_alone() -> None:
    plain = "import Mathlib\n\ndef Opn.x : Nat := 1\n\nexample : Opn.x = 1 := rfl\n"
    assert checks.count_heartbeats_text(plain) == (plain, [])


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        (used(4, "7:6", 31), (4, 31, 200000)),
        (used(4, "9:9", 11225, "greater", 5000), (4, 11225, 5000)),
        ("-:4:0-7:6: info: Try this:\n  [apply] set_option maxHeartbeats 20000 in\n", None),
        ("-:8:60-9:17: error: unexpected token '#count_heartbeats'; expected 'lemma'\n", None),
    ],
)
def test_the_checkers_message_is_read_as_it_prints_it(message: str, expected: Any) -> None:
    assert checks.heartbeats_message(message) == expected


def test_each_count_is_named_by_the_declaration_under_its_own_line() -> None:
    """By the text the checker echoes, not by counting inserted lines: the checker replaces the
    header, and the definitions and Context are inlined above the caller's text."""
    text, _ = checks.count_heartbeats_text(CONTENT)
    found = checks.heartbeats_of(three_counts(text))
    assert found == [
        {"declaration": "Opn.hb_one", "heartbeats": 31, "cap": 200000, "over_cap": False},
        {"declaration": "Opn.hb_two", "heartbeats": 63, "cap": 200000, "over_cap": False},
        {"declaration": "Opn.hb_three", "heartbeats": 9, "cap": 200000, "over_cap": False},
    ]


def test_a_count_over_the_cap_is_reported_as_over() -> None:
    text, _ = checks.count_heartbeats_text(CONTENT)
    body = measured_body(
        text, (31, "less", 200000), (280113, "greater", 200000), (9, "less", 200000)
    )
    over = checks.heartbeats_of(body)[1]
    assert over == {
        "declaration": "Opn.hb_two",
        "heartbeats": 280113,
        "cap": 200000,
        "over_cap": True,
    }


# --- the route ------------------------------------------------------------------------------------


def test_heartbeats_true_answers_the_counts_beside_the_unchanged_verdict() -> None:
    h = harness()
    r = post(h, {"target_id": TARGET, "content": CONTENT, "heartbeats": True})
    assert r.status_code == 200, r.text
    doc = r.json()
    block = doc["heartbeats"]
    assert [d["declaration"] for d in block["declarations"]] == [
        "Opn.hb_one",
        "Opn.hb_two",
        "Opn.hb_three",
    ]
    assert [d["heartbeats"] for d in block["declarations"]] == [31, 63, 9]
    assert block["error"] is None and block["authoritative"] is False
    assert "fast checker" in block["measured_by"] and COMMAND in block["measured_by"]
    assert "without the cap" in block["note"]
    # the verdict is the text's own: the call that is judged never saw the command
    (plain,) = [c for c in h.axle.calls if COMMAND not in c.content]
    assert plain.content == CONTENT
    (measure,) = measuring_calls(h)
    assert measure.content == MEASURED
    assert doc["okay"] is True and COMMAND not in str(doc["result"])


def test_without_the_field_nothing_changes() -> None:
    h = harness()
    r = post(h, {"target_id": TARGET, "content": CONTENT})
    assert r.status_code == 200, r.text
    assert "heartbeats" not in r.json()
    assert len(h.axle.calls) == 1 and measuring_calls(h) == []
    r = post(h, {"target_id": TARGET, "content": CONTENT, "heartbeats": False})
    assert "heartbeats" not in r.json() and measuring_calls(h) == []


def test_the_two_calls_run_side_by_side() -> None:
    """One function, one budget: the measuring call is in flight with the check, not after it."""
    h = harness(barrier=threading.Barrier(2, timeout=5))
    r = post(h, {"target_id": TARGET, "content": CONTENT, "heartbeats": True})
    assert r.status_code == 200, r.text
    assert len(h.axle.calls) == 2


def test_verify_mode_measures_too_and_judges_the_plain_text() -> None:
    h = harness(lambda text: measured_body(text, (12, "less", 200000)))
    proof = "theorem OpnProp.and_reassoc : True := by\n  trivial\n"
    r = post(
        h,
        {
            "target_id": TARGET,
            "node_id": NODE,
            "mode": "verify",
            "content": proof,
            "heartbeats": True,
        },
    )
    assert r.status_code == 200, r.text
    (verify,) = [c for c in h.axle.calls if c.method == "verify_proof"]
    assert COMMAND not in verify.content
    (measure,) = measuring_calls(h)
    assert (
        measure.method == "check" and COMMAND + "\ntheorem OpnProp.and_reassoc" in measure.content
    )


@pytest.mark.parametrize(
    ("reply", "code"),
    [
        (AxleError("AXLE check returned 502", status=502), "upstream-unavailable"),
        (AxleError("AXLE check failed: ReadTimeout", timed_out=True), "check-timeout"),
        (
            {"error": "lean worker timeout", "error_type": "LeanTimeout", "info": {}},
            "check-timeout",
        ),
    ],
)
def test_a_measurement_that_fails_never_costs_the_check(reply: Any, code: str) -> None:
    """C7: the check is answered as it would have been; the block says the measurement was not
    made and why. A declaration far over the cap can outlast the 20 s budget, which is the case
    that matters most and the one this cannot always measure."""
    h = harness(reply)
    r = post(h, {"target_id": TARGET, "content": CONTENT, "heartbeats": True})
    assert r.status_code == 200, r.text
    doc = r.json()
    assert doc["okay"] is True
    assert doc["heartbeats"]["declarations"] == []
    assert doc["heartbeats"]["error"] == code


def test_a_measurement_that_breaks_is_logged_and_never_costs_the_check() -> None:
    """Not only the failures the seam names: anything the measuring half raises."""

    def broken(_text: str) -> dict[str, Any]:
        msg = "a bug in the measuring half"
        raise RuntimeError(msg)

    h = harness(broken)
    r = post(h, {"target_id": TARGET, "content": CONTENT, "heartbeats": True})
    assert r.status_code == 200, r.text
    assert r.json()["okay"] is True
    assert r.json()["heartbeats"]["error"] == "measurement-failed"


def test_a_theorem_the_copy_could_not_count_is_said() -> None:
    """Three commands went in and two counts came back (the third declaration did not get that
    far): the answer names the one with no figure rather than hand back a short list."""
    h = harness(
        lambda text: (
            measured_body(text[: text.rindex(COMMAND)], (31, "less", 200000), (63, "less", 200000))
            | {"content": text}
        )
    )
    doc = post(h, {"target_id": TARGET, "content": CONTENT, "heartbeats": True}).json()
    assert [d["declaration"] for d in doc["heartbeats"]["declarations"]] == [
        "Opn.hb_one",
        "Opn.hb_two",
    ]
    assert doc["heartbeats"]["not_measured"] == ["Opn.hb_three"]


def test_nothing_to_count_spends_no_second_call() -> None:
    h = harness()
    plain = "import Mathlib\n\nexample : (1 : ℕ) = 1 := rfl\n"
    doc = post(h, {"target_id": TARGET, "content": plain, "heartbeats": True}).json()
    assert doc["heartbeats"]["declarations"] == []
    assert doc["heartbeats"]["error"] == "no-theorem"
    assert len(h.axle.calls) == 1


def test_the_measurement_is_charged_and_logged_as_its_own_check() -> None:
    h = harness()
    doc = post(h, {"target_id": TARGET, "content": CONTENT, "heartbeats": True}).json()
    modes = sorted(record.mode for record in h.store.checks.values())
    assert modes == ["check", "heartbeats"]
    assert doc["heartbeats"]["log_id"] in h.store.checks
    assert doc["heartbeats"]["log_id"] != doc["log_id"]


def test_a_spent_budget_skips_the_measurement_not_the_check() -> None:
    h = harness_with({"OPN_API_ANONYMOUS_CHECKS_PER_DAY": "1"}, axle=MeasuringAxle())
    seed(h)
    r = post(h, {"target_id": TARGET, "content": CONTENT, "heartbeats": True})
    assert r.status_code == 200, r.text
    assert r.json()["heartbeats"]["error"] == "rate-limited"
    assert measuring_calls(h) == []


def test_heartbeats_is_for_a_proof_text() -> None:
    h = harness()
    r = post(h, {"target_id": TARGET, "node_id": NODE, "mode": "witness", "heartbeats": True})
    refused(r, 400, "heartbeats-not-used")
    r = post(h, {"target_id": TARGET, "node_id": NODE, "mode": "hazards", "heartbeats": True})
    refused(r, 400, "heartbeats-not-used")
    r = post(h, {"target_id": TARGET, "content": CONTENT, "heartbeats": "yes"})
    refused(r, 400, "heartbeats-invalid")
    assert h.axle.calls == []


def test_check_lean_forwards_the_field() -> None:
    h = harness()
    with h.client:
        client = McpClient(h)
        answer = client.ok(
            "check_lean", {"target_id": TARGET, "content": CONTENT, "heartbeats": True}
        )
    assert answer["status"] == 200
    assert [d["heartbeats"] for d in answer["body"]["heartbeats"]["declarations"]] == [31, 63, 9]
