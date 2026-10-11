"""F07-T67 (audit 2026-10-04): open pull requests are capped per pseudonym and for the graph.

Nothing bounded how many pull requests one identity could hold open: the write limit is per
hour, so an identity could keep adding to the queue every hour, and the merge actor considers
every open pull request in number order (F05-Q19) — one caller could starve everyone behind it.
Nor was there any bound on the whole queue, which is what the graph's single runner pool pays for.

``submissions.open_pr`` is the one place every route opens a pull request (appends, proposals,
witnesses, submissions), so the caps live there:

- per pseudonym (``OPN_API_OPEN_PRS_PER_IDENTITY``): 429 ``open-pull-requests-cap`` naming the
  caller's open pull requests in ``details.open``. Only when the caller is at the cap are their
  records reconciled against the host (``pending.reconcile``), so a merged pull request nobody
  has asked about does not count against them;
- for the graph (``OPN_API_OPEN_PRS_GLOBAL``): 503 ``queue-full`` with ``Retry-After``, counted
  against the host's open listing when the store's count reaches the cap.

Both are published in ``info.json``'s ``rate_limit_policy``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from api_fakes import TUTORIAL_NODE, Harness, make_harness, make_precheck_key
from test_appends import postmortem
from test_submissions import submit


def harness(**env: str) -> Harness:
    return make_harness(env)


def note(h: Harness, token: str, n: int) -> Any:
    """A distinct postmortem, one second after the last (a record's name is to the second)."""
    h.clock.advance(seconds=1)
    body = {"node_id": TUTORIAL_NODE, "yaml": postmortem(detail=f"attempt number {n}")}
    return h.client.post("/postmortems", json=body, headers=h.auth(token))


def test_an_identity_at_its_cap_is_refused_with_its_open_pull_requests() -> None:
    h = harness(OPN_API_OPEN_PRS_PER_IDENTITY="2")
    alice = h.token_for("code_alice", "alice")
    numbers = []
    for n in range(2):
        r = note(h, alice, n)
        assert r.status_code == 201, r.text
        numbers.append(r.json()["pr_number"])
    over = note(h, alice, 2)
    assert over.status_code == 429, over.text
    doc = over.json()
    assert doc["error"] == "open-pull-requests-cap"
    assert sorted(o["pr_number"] for o in doc["details"]["open"]) == numbers
    assert all(o["pr_url"].endswith(f"/pull/{o['pr_number']}") for o in doc["details"]["open"])
    assert doc["details"]["cap"] == 2
    assert int(over.headers["retry-after"]) > 0  # every 429 carries one (the guide's promise)
    assert len(h.githost.pulls) == 2
    # Another identity is not held to Alice's cap.
    bob = h.token_for("code_bob", "bob")
    assert note(h, bob, 3).status_code == 201


def test_a_merged_pull_request_frees_the_slot_without_anyone_asking_about_it() -> None:
    h = harness(OPN_API_OPEN_PRS_PER_IDENTITY="2")
    alice = h.token_for("code_alice", "alice")
    for n in range(2):
        assert note(h, alice, n).status_code == 201
    h.githost.set_pull_request_state(1, state="closed", merged=True)
    r = note(h, alice, 2)
    assert r.status_code == 201, r.text
    assert h.store.get_submission_by_pr(1).closed is not None  # type: ignore[union-attr]


def test_the_cap_holds_at_the_one_place_every_route_opens(tmp_path: Path) -> None:
    """A proof submission counts with the appends: the cap is at ``open_pr``."""
    h = harness(OPN_API_OPEN_PRS_PER_IDENTITY="1")
    alice = h.token_for("code_alice", "alice")
    assert note(h, alice, 0).status_code == 201
    job = h.tutorial_job(make_precheck_key(tmp_path), token=alice)
    r = submit(h, alice, precheck_job_id=job["id"])
    assert r.status_code == 429, r.text
    assert r.json()["error"] == "open-pull-requests-cap"
    # The job was not spent by the refusal (F06-T11): it opens once the slot is free.
    h.githost.set_pull_request_state(1, state="closed", merged=True)
    h.context.open_pulls = None  # the listing's window (pull_listing_max_stale_s) has passed
    assert submit(h, alice, precheck_job_id=job["id"]).status_code == 201


def test_a_full_queue_is_a_503_with_retry_after() -> None:
    h = harness(OPN_API_OPEN_PRS_GLOBAL="2")
    alice = h.token_for("code_alice", "alice")
    bob = h.token_for("code_bob", "bob")
    assert note(h, alice, 0).status_code == 201
    assert note(h, bob, 1).status_code == 201
    full = note(h, alice, 2)
    assert full.status_code == 503, full.text
    assert full.json()["error"] == "queue-full"
    assert int(full.headers["retry-after"]) > 0
    assert len(h.githost.pulls) == 2
    # The host's listing is the recount: a merged pull request no longer fills the queue.
    h.githost.set_pull_request_state(2, state="closed", merged=True)
    h.context.open_pulls = None  # the listing's window (pull_listing_max_stale_s) has passed
    assert note(h, alice, 3).status_code == 201


def test_both_caps_are_published() -> None:
    h = harness(OPN_API_OPEN_PRS_PER_IDENTITY="7", OPN_API_OPEN_PRS_GLOBAL="70")
    policy = h.client.get("/info.json").json()["rate_limit_policy"]
    assert policy["open_pull_requests_per_identity"] == 7
    assert policy["open_pull_requests_global"] == 70
