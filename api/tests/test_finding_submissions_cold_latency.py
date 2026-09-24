"""F07-T39 (testers 2026-09-24): ``GET /submissions.json`` took up to 29 s cold.

The story. The erdos-1050 MCP agent twice, and the erdos-69 MCP agent once, waited 20 to 29
seconds for ``list_submissions`` while the queue held about twenty open pull requests; the lead
measured it live at 28.5 s cold with 22 open, then 0.7 s and 0.5 s inside the cache window
(``engineering/session-notes/2026-09-24-calibration-testers.md``, finding 3).

The mechanism. ``pending.snapshot`` reconciles every open record against the host so that "open"
means the host still calls it open (2026-09-16). It did so one record after another, and each
lookup (``HttpxGitHost.get_pull_request``) is three or four GitHub API round trips (the pull, its
reviews, the runs on its head, and a run's jobs where the colour is ambiguous). The cost grew
with the queue: twenty-two records at about 1.3 s each.

The rule. The host lookups run concurrently on a bounded pool whose width is configuration
(``OPN_API_RECONCILE_CONCURRENCY``, default 8, C6); the snapshot is the same document the serial
one was, in the same order. Reconciling a record (its live state, a racer's conversion, closing
it) holds a per-pull-request lock, so two readers at once never convert a losing racer twice.
One lookup that fails leaves its row listed with the rest reconciled (C7). The seam opens one
HTTP client per lookup, not one per call.

Timing assertions are generous by design: the concurrent snapshot must take under 60 % of the
serial time, and concurrency is asserted directly as the most lookups the fake host saw in flight
at once.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import pytest
from api_fakes import Harness, make_harness
from test_finding_racer_alternate import racing, replaced
from test_githost_seam import (  # the seam's fixtures, reused as they stand
    ACTION_RUNS,
    HEAD_SHA,
    PULL,
    REPO,
    REVIEWS,
    Script,
    host,
    install_app,
    pem,
    rsa_key,
    script,
)
from test_pending_submissions import record

from opn_api import githost, pending
from opn_api.githost import HttpxGitHost
from opn_api.store import MemoryStore

__all__ = ["host", "pem", "rsa_key", "script"]  # fixtures, imported for pytest to find

LATENCY = 0.2
OPEN = 25


def harness_with(env: dict[str, str] | None = None) -> Iterator[Harness]:
    h = make_harness(env)
    with h.client:
        yield h


@pytest.fixture
def queue() -> Iterator[Harness]:
    yield from harness_with()


def fill(h: Harness, count: int = OPEN, *, merged: frozenset[int] = frozenset()) -> None:
    """``count`` open records, each an open pull request on the host, except ``merged``."""
    for number in range(1, count + 1):
        h.store.put_submission(record(number, kind="annex"))
        if number in merged:
            h.githost.set_pull_request_state(number, state="closed", merged=True)
        else:
            h.githost.set_pull_request_state(number, mergeable_state="behind")


def timed_snapshot(h: Harness) -> tuple[float, dict[str, Any]]:
    start = time.monotonic()
    r = h.client.get("/submissions.json")
    elapsed = time.monotonic() - start
    assert r.status_code == 200, r.text
    doc: dict[str, Any] = r.json()
    return elapsed, doc


def test_twenty_five_open_records_answer_within_four_lookups_of_time(queue: Harness) -> None:
    """At 0.2 s a lookup, 25 records serially is 5 s; eight at a time is four rounds (0.8 s).
    The bound is 60 % of serial, so only a snapshot that is not concurrent can miss it."""
    fill(queue)
    queue.githost.pull_latency_s = LATENCY
    elapsed, doc = timed_snapshot(queue)
    assert len(doc["open"]) == OPEN
    assert queue.githost.pulls_max_in_flight > 1, "the lookups ran one at a time"
    assert elapsed < 0.6 * OPEN * LATENCY, elapsed


def test_the_width_is_configuration_and_bounds_the_lookups_in_flight() -> None:
    for h in harness_with({"OPN_API_RECONCILE_CONCURRENCY": "3"}):
        fill(h, 12)
        h.githost.pull_latency_s = 0.05
        timed_snapshot(h)
        assert 1 < h.githost.pulls_max_in_flight <= 3, h.githost.pulls_max_in_flight


def test_the_concurrent_snapshot_equals_the_serial_one() -> None:
    """Same records, same order, same fields: the pool changes the time, not the answer."""
    answers = []
    for width in ("1", "8"):
        for h in harness_with({"OPN_API_RECONCILE_CONCURRENCY": width}):
            fill(h, 12, merged=frozenset({2, 5, 11}))
            h.githost.pull_latency_s = 0.01
            _, doc = timed_snapshot(h)
            answers.append(doc["open"])
            assert [e["pr_number"] for e in doc["open"]] == [1, 3, 4, 6, 7, 8, 9, 10, 12]
    assert answers[0] == answers[1]


def test_one_failing_lookup_leaves_its_row_listed_and_the_rest_reconciled(queue: Harness) -> None:
    fill(queue, 10, merged=frozenset({5}))
    queue.githost.pull_failures = {3}
    _, doc = timed_snapshot(queue)
    assert [e["pr_number"] for e in doc["open"]] == [1, 2, 3, 4, 6, 7, 8, 9, 10]
    assert queue.store.get_submission_by_pr(3).closed is None  # type: ignore[union-attr]
    assert queue.store.get_submission_by_pr(5).closed is not None  # type: ignore[union-attr]


def test_a_losing_racer_is_converted_once_under_concurrency(
    queue: Harness, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Four readers reconcile at once. The store's counter is the cross-process guard, but the
    memory store's read-then-write is not atomic between threads; the per-pull-request lock is
    what keeps one process from converting the racer twice. The counter is slowed to widen that
    window, so the test does not depend on the scheduler's luck."""
    _node, _loser = racing(queue)
    fill(queue, 8)  # numbers 1-8; the racer is #12
    queue.githost.pull_latency_s = 0.05
    real = MemoryStore.bump_counter

    def slow_bump(self: MemoryStore, key: str, expires: Any) -> int:
        count, _ = self.counters.get(key, (0, expires))
        time.sleep(0.05)
        self.counters[key] = (int(count) + 1, expires)
        return int(count) + 1

    monkeypatch.setattr(MemoryStore, "bump_counter", slow_bump)
    start = threading.Barrier(4)

    def read(_: int) -> dict[str, Any]:
        start.wait()
        return pending.snapshot(queue.context)

    with ThreadPoolExecutor(4) as pool:
        list(pool.map(read, range(4)))
    monkeypatch.setattr(MemoryStore, "bump_counter", real)
    assert len(replaced(queue)) == 1, [p.branch for p in replaced(queue)]


def test_get_pull_request_opens_one_client(
    script: Script, host: HttpxGitHost, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The seam: one lookup, four API calls (the pull, its reviews, the runs, a run's jobs), one
    ``httpx.Client`` and so one connection pool. Counted after the installation token exists,
    whose exchange is its own client once an hour."""
    install_app(script).on(
        "GET",
        PULL,
        json={
            "number": 33,
            "state": "open",
            "mergeable_state": "blocked",
            "head": {"sha": HEAD_SHA},
        },
    ).on("GET", REVIEWS, json=[]).on(
        "GET",
        ACTION_RUNS,
        json={"workflow_runs": [{"id": 9, "name": "gate", "status": "in_progress"}]},
    ).on("GET", f"/repos/{REPO}/actions/runs/9/jobs", json={"jobs": []})
    host.get_pull_request(REPO, 33)  # mints and caches the installation token
    made: list[int] = []
    shim: Any = vars(githost)["httpx"]  # the fixture's stand-in for the module
    inner = shim._client

    class Counting(inner):  # type: ignore[misc, valid-type]
        def __init__(self, **kwargs: Any) -> None:
            made.append(1)
            super().__init__(**kwargs)

    monkeypatch.setattr(shim, "_client", Counting)
    before = len(script.calls)
    host.get_pull_request(REPO, 33)
    assert len(script.calls) - before == 4
    assert made == [1]


def test_concurrent_lookups_on_a_cold_process_mint_one_installation_token(
    script: Script, host: HttpxGitHost
) -> None:
    """The pool makes the first snapshot of a fresh process ask for the App's installation token
    from eight threads at once. Each would mint its own (a JWT signature and two API calls, and
    an hour-long token thrown away); the cache is filled once, under a lock."""
    install_app(script)
    answer = script.handler

    def slow(request: Any) -> Any:
        time.sleep(0.05)
        return answer(request)

    script.handler = slow  # type: ignore[method-assign]
    start = threading.Barrier(8)

    def token(_: int) -> str:
        start.wait()
        return host._installation_token(REPO)

    with ThreadPoolExecutor(8) as pool:
        tokens = set(pool.map(token, range(8)))
    assert len(tokens) == 1
    assert len(script.to("POST", "/app/installations/99/access_tokens")) == 1
