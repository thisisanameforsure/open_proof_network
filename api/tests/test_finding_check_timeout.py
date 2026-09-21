"""F13-T13: a slow check is answered by the service, never killed under it (tester 2026-09-21).

The erdos-1050 agent sent ``exact?`` through ``POST /check`` and got a raw
``500 {"message":"Internal Server Error"}`` after 15.6 s: the function's own timeout (15 s) was
shorter than the budget the service gave the checker (60 s plus a 10 s connect allowance), so the
function died before it could answer in its own shape, and no record was written.

Each test here asserts the correct behaviour and was seen red first
(``engineering/evidence/F13/task-13.txt``).
"""

from __future__ import annotations

import re
import threading
import time
from pathlib import Path
from typing import Any

import httpx
import pytest
from api_fakes import FakeAxle
from mcp_client import TARGET
from test_checks import PROOF, Blocking, harness_with, post, refused, seed

from opn_api import axle, checks, config
from opn_api.axle import AxleError

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / "api" / "infra" / "api.cfn.yaml"
#: What the function needs besides the checker: the graph reads before it and the record after.
HEADROOM_S = 2

#: The hosted checker's own answer when its budget runs out, as probed 2026-09-21 (status 200).
LEAN_TIMEOUT = {
    "error": "lean worker timeout after 20.0s",
    "exit_status": -9,
    "error_type": "LeanTimeout",
    "info": {"request_id": "req-timeout"},
}


def function_timeout_s() -> int:
    (match,) = re.findall(r"^\s+Timeout: (\d+)\s*$", TEMPLATE.read_text("utf-8"), re.M)
    return int(match)


def test_the_checkers_whole_budget_fits_inside_the_functions_timeout() -> None:
    """The wait for a slot, the connect allowance, the checker's budget and the read grace, added
    up, leave the function time to answer. Read from the template and the code, not restated."""
    worst = (
        checks.SLOT_WAIT_S
        + axle.CONNECT_TIMEOUT_S
        + config.DEFAULT_CHECK_TIMEOUT_S
        + axle.READ_GRACE_S
    )
    assert worst + HEADROOM_S <= function_timeout_s(), (worst, function_timeout_s())
    assert function_timeout_s() < 30  # the HTTP API's own integration ceiling


def test_a_checker_that_ran_out_of_time_is_a_named_refusal_with_a_record() -> None:
    """Both shapes: the checker's own ``LeanTimeout`` answer, and a transport that timed out."""
    body = {"target_id": TARGET, "content": PROOF}
    for reply in (LEAN_TIMEOUT, AxleError("AXLE check failed: ReadTimeout", timed_out=True)):
        replies: list[Any] = [reply]
        h = harness_with(axle=FakeAxle(replies=replies))
        seed(h)
        doc = refused(post(h, body), 504, "check-timeout")
        assert str(h.settings.check_timeout_s) in doc["message"]
        assert "exact?" in doc["message"]  # says what does not fit, not only that it failed
        record = h.store.checks[doc["details"]["log_id"]]
        assert record.outcome == "check-timeout"
        assert doc["details"]["budget_s"] == h.settings.check_timeout_s


def test_a_transport_timeout_is_marked_by_the_client(monkeypatch: pytest.MonkeyPatch) -> None:
    """The seam itself: httpx's timeout becomes an ``AxleError`` that says so."""

    def slow(_request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow")

    class Slow(httpx.Client):
        def __init__(self, **kwargs: Any) -> None:
            super().__init__(transport=httpx.MockTransport(slow), **kwargs)

    monkeypatch.setattr(httpx, "Client", Slow)
    with pytest.raises(AxleError) as caught:
        axle.HttpxAxle(base_url="https://axle.invalid").check("x", environment="e", timeout_s=1)
    assert caught.value.timed_out is True and caught.value.status is None


def test_a_full_cap_answers_busy_after_the_slot_wait_not_the_checkers_budget() -> None:
    """The wait for a slot is its own short budget: with a 20 s checker budget a full cap used to
    hold the second caller for all 20 s, most of the function's life."""
    assert checks.SLOT_WAIT_S <= 5
    blocking = Blocking()
    h = harness_with({"OPN_API_CHECK_CONCURRENCY": "1", "OPN_API_CHECK_TIMEOUT_S": "20"}, blocking)
    seed(h)
    body = {"target_id": TARGET, "content": PROOF}
    first: list[httpx.Response] = []
    worker = threading.Thread(target=lambda: first.append(post(h, body)))
    worker.start()
    try:
        assert blocking.entered.wait(10)
        started = time.monotonic()
        refused(post(h, body), 503, "checker-busy")
        assert time.monotonic() - started < checks.SLOT_WAIT_S + 3
    finally:
        blocking.release.set()
        worker.join(20)
