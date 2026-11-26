"""mcpfix WB2 item 1 (testers 2026-11-25, t257 item 5 and t257b item 13): get_submission's
``pull_request`` block went backwards and called itself fresh.

The block was cached per process (``Context.pulls``), and the service runs as up to twenty Lambda
instances, so two calls a minute apart could land on two instances and the second answered an
*older* read (``read_at`` 22:55:11 after 22:52:06 ... and back), each with ``stale: false``.

Now every fresh read is written through to the shared store, and a read serves the newer of the
process's copy and the stored one, so ``read_at`` never moves backwards across instances. The
block carries ``age_s``, seconds since ``read_at``, and ``stale`` is also true once that age is
past ``pull_max_stale_s`` (``pull_request_error`` still says why a read failed).

Two applications sharing one store, one host and one clock stand for two instances, over both
store implementations.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from api_fakes import FakeClock, FakeGitHost, Harness, alice, bob, make_harness
from test_pending_submissions import proof_record
from test_store_seam import dynamo

from opn_api.store import MemoryStore, Store

GATE_RUNNING = {"name": "gate", "status": "in_progress", "conclusion": None, "url": "u"}


@pytest.fixture(params=["memory", "dynamodb"])
def shared(request: pytest.FixtureRequest) -> Store:
    return MemoryStore() if request.param == "memory" else dynamo()


@pytest.fixture
def pair(shared: Store) -> Iterator[tuple[Harness, Harness]]:
    githost = FakeGitHost.with_fixtures(code_alice=alice(), code_bob=bob())
    clock = FakeClock()
    a = make_harness(store=shared, githost=githost, clock=clock)
    b = make_harness(store=shared, githost=githost, clock=clock)
    with a.client, b.client:
        yield a, b


def block(h: Harness, number: int = 7) -> dict[str, Any]:
    r = h.client.get(f"/submissions/{number}")
    assert r.status_code == 200, r.text
    doc: dict[str, Any] = r.json()["pull_request"]
    return doc


def test_read_at_never_moves_backwards_across_instances(pair: tuple[Harness, Harness]) -> None:
    a, b = pair
    proof_record(a)
    a.githost.set_pull_request_state(7)
    first = block(a)
    assert first["read_at"] == "2026-09-09T12:00:00Z" and first["runs"] == []

    late = a.settings.pull_max_stale_s + 20
    a.clock.advance(seconds=late)
    a.githost.set_pull_request_state(7, runs=[GATE_RUNNING])
    second = block(b)  # the other instance: the shared snapshot is past the window, so it reads
    assert second["read_at"] == "2026-09-09T12:03:20Z" and len(second["runs"]) == 1

    a.clock.advance(seconds=10)
    third = block(a)  # back on the first instance, whose own copy is the older one
    assert third["read_at"] == "2026-09-09T12:03:20Z", third
    assert len(third["runs"]) == 1
    assert third["age_s"] == 10
    assert third["stale"] is False


def test_the_newer_snapshot_costs_no_host_read(pair: tuple[Harness, Harness]) -> None:
    a, b = pair
    proof_record(a)
    a.githost.set_pull_request_state(7)
    block(a)
    a.clock.advance(seconds=a.settings.pull_max_stale_s + 20)
    block(b)  # past the window: instance b reads the host, and shares the read
    reads = len(a.githost.pull_lookups)
    a.clock.advance(seconds=5)
    assert block(a)["read_at"] == "2026-09-09T12:03:20Z"
    assert len(a.githost.pull_lookups) == reads  # instance a took instance b's read


def test_a_snapshot_older_than_the_window_is_stale(pair: tuple[Harness, Harness]) -> None:
    a, _ = pair
    proof_record(a)
    a.githost.set_pull_request_state(7)
    assert block(a)["stale"] is False
    a.clock.advance(seconds=a.settings.pull_max_stale_s + 30)
    late = block(a)
    assert late["stale"] is True
    assert late["age_s"] == a.settings.pull_max_stale_s + 30


def test_a_host_failure_is_still_stale_with_its_error(pair: tuple[Harness, Harness]) -> None:
    a, _ = pair
    proof_record(a)
    a.githost.set_pull_request_state(7)
    block(a)
    for entry in a.context.pulls.values():
        entry.fetched_at -= a.settings.pull_max_stale_s + 1
    a.githost.pr_lookup_failure = "502"
    r = a.client.get("/submissions/7").json()
    assert r["pull_request"]["stale"] is True and r["pull_request_error"]


def test_a_forgotten_pull_request_is_read_afresh_on_every_instance(
    pair: tuple[Harness, Harness],
) -> None:
    """A route that moved a pull request's head drops its copy (``pending.forget_pull``); the
    stored snapshot goes too, or another instance would serve the old head as fresh."""
    from opn_api import pending  # noqa: PLC0415

    a, b = pair
    proof_record(a)
    a.githost.set_pull_request_state(7, head_sha="1" * 40)
    block(a)
    a.githost.set_pull_request_state(7, head_sha="2" * 40)
    pending.forget_pull(a.context, 7)
    assert block(b)["head_sha"] == "2" * 40
