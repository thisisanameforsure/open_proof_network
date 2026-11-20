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
from test_pending_submissions import TARGET
from test_submissions import submit

from opn_api import clock as clockmod
from opn_api import config
from opn_api.store import Submission


def harness(**env: str) -> Harness:
    return make_harness(env)


def note(h: Harness, token: str, n: int) -> Any:
    """A distinct postmortem, one second after the last (a record's name is to the second)."""
    h.clock.advance(seconds=1)
    body = {"node_id": TUTORIAL_NODE, "yaml": postmortem(detail=f"attempt number {n}")}
    return h.client.post("/postmortems", json=body, headers=h.auth(token))


def test_an_identity_at_its_cap_is_refused_with_its_open_pull_requests() -> None:
    h = harness(OPN_API_OPEN_APPENDS_PER_IDENTITY="2")  # postmortems: the append cap (F07-T84)
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
    h = harness(OPN_API_OPEN_APPENDS_PER_IDENTITY="2")  # postmortems: the append cap (F07-T84)
    alice = h.token_for("code_alice", "alice")
    for n in range(2):
        assert note(h, alice, n).status_code == 201
    h.githost.set_pull_request_state(1, state="closed", merged=True)
    r = note(h, alice, 2)
    assert r.status_code == 201, r.text
    assert h.store.get_submission_by_pr(1).closed is not None  # type: ignore[union-attr]


def test_the_cap_holds_at_the_one_place_every_route_opens(tmp_path: Path) -> None:
    """A proof submission is held at ``open_pr`` like every route. Restated for F07-T84: it was a
    postmortem that filled the slot, which is the defect B3 (an append counts in its own cap now);
    the slot is filled by a proof of the caller's here, and the job is still not spent."""
    h = harness(OPN_API_OPEN_PRS_PER_IDENTITY="1")
    alice = h.token_for("code_alice", "alice")
    seed_open(h, 100, "proof", "alice")
    job = h.tutorial_job(make_precheck_key(tmp_path), token=alice)
    r = submit(h, alice, precheck_job_id=job["id"])
    assert r.status_code == 429, r.text
    assert r.json()["error"] == "open-pull-requests-cap"
    # The job was not spent by the refusal (F06-T11): it opens once the slot is free.
    h.githost.set_pull_request_state(100, state="closed", merged=True)
    h.context.open_pulls = None  # the listing's window (pull_listing_max_stale_s) has passed
    assert submit(h, alice, precheck_job_id=job["id"]).status_code == 201


# --- F07-T84 (bug B3): appends count against a cap of their own ----------------------------------


def seed_open(h: Harness, number: int, kind: str, pseudonym: str) -> None:
    """An open pull request the service opened for ``pseudonym``: its record, and the host's
    listing entry on the branch the route of ``kind`` opens (``submit/`` for a proof)."""
    branch = ("submit/" if kind in ("proof", "partial") else "append/") + f"seed-{number}"
    h.store.put_submission(
        Submission(
            id=f"01M{number:023d}",
            kind=kind,
            node_id=TUTORIAL_NODE,
            target_id=TARGET,
            pr_number=number,
            pr_url=f"https://github.com/pr/{number}",
            pseudonym=pseudonym,
            precheck_job_id=None,
            created=clockmod.render(h.clock.now()),
        )
    )
    h.githost.set_pull_request_state(number, head_ref=branch)


def test_an_identity_with_ten_open_appends_can_still_open_a_proof(tmp_path: Path) -> None:
    h = harness()
    alice = h.token_for("code_alice", "alice")
    for n in range(10):
        assert note(h, alice, n).status_code == 201
    job = h.tutorial_job(make_precheck_key(tmp_path), token=alice)
    r = submit(h, alice, precheck_job_id=job["id"])
    assert r.status_code == 201, r.text
    over = note(h, alice, 10)
    assert over.status_code == 429, over.text  # the eleventh append is held to the append cap
    doc = over.json()
    assert doc["error"] == "open-pull-requests-cap"
    assert doc["details"]["cap_name"] == "open_appends_per_identity"
    assert doc["details"]["half"] == "append" and "append" in doc["message"]
    assert len(doc["details"]["open"]) == 10  # the appends, not the proof


def test_an_identity_with_ten_open_proofs_can_still_open_an_append() -> None:
    h = harness()
    alice = h.token_for("code_alice", "alice")
    for number in range(100, 110):
        seed_open(h, number, "proof", "alice")
    r = note(h, alice, 0)
    assert r.status_code == 201, r.text


def test_a_building_refusal_names_the_building_cap(tmp_path: Path) -> None:
    h = harness(OPN_API_OPEN_PRS_PER_IDENTITY="2")
    alice = h.token_for("code_alice", "alice")
    for number in (100, 101):
        seed_open(h, number, "proof", "alice")
    job = h.tutorial_job(make_precheck_key(tmp_path), token=alice)
    r = submit(h, alice, precheck_job_id=job["id"])
    assert r.status_code == 429, r.text
    doc = r.json()
    assert doc["details"]["cap_name"] == "open_pull_requests_per_identity"
    assert doc["details"]["half"] == "build" and doc["details"]["cap"] == 2
    assert sorted(o["pr_number"] for o in doc["details"]["open"]) == [100, 101]


def test_the_append_cap_is_its_own_setting() -> None:
    h = harness(OPN_API_OPEN_APPENDS_PER_IDENTITY="1")
    alice = h.token_for("code_alice", "alice")
    assert note(h, alice, 0).status_code == 201
    over = note(h, alice, 1)
    assert over.status_code == 429, over.text
    assert over.json()["details"]["cap"] == 1


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


def test_the_append_cap_is_published() -> None:
    h = harness(OPN_API_OPEN_APPENDS_PER_IDENTITY="12")
    assert h.client.get("/info.json").json()["rate_limit_policy"]["open_appends_per_identity"] == 12
    default = harness().client.get("/info.json").json()["rate_limit_policy"]
    assert default["open_appends_per_identity"] == config.DEFAULT_OPEN_PRS_PER_IDENTITY
