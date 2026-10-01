"""F05-T18 (testers 2026-10-01; the owner, 2026-10-01: "Yes, show queue positions"): where a
submission stands in the merge queue, and five things the same two routes said wrongly.

Six agents asked for it (C1). With fifteen pull requests open an agent could see its own
``waiting_on: merge`` and nothing about the fourteen ahead; #359 was green at 17:41 and merged at
18:05:50 behind three witnesses and two annexes it could not see.

The position is the merge actor's own order, read from the graph's ``merge.yml``
(``candidates``): open, non-draft pull requests on a branch the service opened, against
``main``, lowest number first. It is derived from the one open-pull-request listing the service
already reads per window (F07-T47), so it costs no host call per record however long the queue
is (2026-09-24: a list that reconciled each item live took 28 s with 22 open).
``gate/tests/test_finding_queue_order_is_the_actors.py`` holds this order to the workflow's.

Fixed while there, each from the bug list:

* A4: after #332 merged, ``GET /submissions/332`` said ``open, waiting_on gate, stale: false``
  for 84 s (#336: 2 m 23 s). The state is cached for 180 s; the listing, read every 60 s, had
  already dropped it.
* A12: a merged proof read ``waiting_on: null`` while its post-merge job ran, where the guide
  says ``products``; and ``submission.closed`` was the time of the first read after the close
  (#360 merged 18:19:10Z, ``closed: 2026-10-01T19:50:21Z``).
* A13: the artifact type is ``kind`` on the read routes and ``artifact_type`` on every write.
"""

from __future__ import annotations

import time
from typing import Any

from api_fakes import TUTORIAL_NODE, Harness
from mcp_client import McpClient
from test_pending_submissions import MERGE_SHA, annex, get, proof_record, seed_attestation

from opn_api import frontier

GREEN = {"name": "gate", "status": "completed", "conclusion": "success", "url": "u"}
RUNNING = {"name": "gate", "status": "in_progress", "conclusion": None, "url": "u"}


def listing(h: Harness) -> dict[str, Any]:
    r = h.client.get("/submissions.json")
    assert r.status_code == 200, r.text
    doc: dict[str, Any] = r.json()
    return doc


def age_listing(h: Harness) -> None:
    """The open listing was read a window and a second ago; the per-pull-request cache is left
    as it is, which is the state A4 was reported in."""
    cached = h.context.open_pulls
    if cached is not None:
        cached.fetched_at = time.monotonic() - (h.settings.pull_listing_max_stale_s + 1)


def cold(h: Harness) -> None:
    """Nothing read yet: opening a pull request reads the open ones (the copy rule, F07-T35),
    so a test that counts reads, or seeds a state, starts from empty caches and counters."""
    h.context.pulls.clear()
    h.context.open_pulls = None
    h.githost.pull_lookups.clear()
    h.githost.listing_calls = 0


def three_annexes(h: Harness) -> list[dict[str, Any]]:
    token = h.token_for("code_alice", "alice")
    opened = [annex(h, token) for _ in range(3)]
    cold(h)
    return opened


# --- the position ---------------------------------------------------------------------------------


def test_a_submission_says_where_it_stands_and_what_is_ahead(harness: Harness) -> None:
    opened = three_annexes(harness)
    harness.githost.set_pull_request_state(1, runs=[RUNNING])
    get(harness, "1")  # somebody asked about #1, so the service holds its state
    doc = get(harness, "3")
    queue = doc.get("queue")
    assert queue is not None, "no queue block"
    assert (queue["position"], queue["of"]) == (3, 3)
    assert [a["pr_number"] for a in queue["ahead"]] == [1, 2]
    first, second = queue["ahead"]
    assert (first["id"], first["kind"], first["node_id"]) == (
        opened[0]["id"],
        "annex",
        TUTORIAL_NODE,
    )
    # what is known of the ones ahead is what the service already read, never a new read
    assert first["waiting_on"] == "gate" and first["waiting_on_read_at"] is not None
    assert second["waiting_on"] is None and second["waiting_on_read_at"] is None
    assert queue["stale"] is False and queue["read_at"] is not None
    assert "oldest first" in queue["order"]
    assert harness.githost.pull_lookups == [1, 3]


def test_the_position_moves_when_the_one_ahead_merges(harness: Harness) -> None:
    three_annexes(harness)
    assert get(harness, "2")["queue"]["position"] == 2
    harness.githost.set_pull_request_state(
        1, state="closed", merged=True, merge_commit_sha=MERGE_SHA
    )
    age_listing(harness)
    queue = get(harness, "2")["queue"]
    assert (queue["position"], queue["of"], queue["ahead"]) == (1, 2, [])


def test_only_what_the_merge_actor_takes_is_counted(harness: Harness) -> None:
    """A draft, a branch the service did not open and a pull request against another base are
    not in the actor's queue; one the service did not record but opened is (it is ahead)."""
    three_annexes(harness)
    host = harness.githost
    host.set_pull_request_state(20, head_ref="feature/by-hand")
    host.set_pull_request_state(21, head_ref="append/a-draft", draft=True)
    host.set_pull_request_state(22, head_ref="propose/unrecorded")
    host.pull_states[23] = {"head_ref": "submit/x", "base_ref": "next"}
    host.pull_states[24] = {"head_ref": "submit/a-fork", "same_repo": False}
    queue = get(harness, "3")["queue"]
    assert (queue["position"], queue["of"]) == (3, 4)
    entries = listing(harness)
    assert entries["queue"]["order"] == [1, 2, 3, 22]


def test_a_finished_submission_has_no_queue(harness: Harness) -> None:
    three_annexes(harness)
    harness.githost.set_pull_request_state(
        1, state="closed", merged=True, merge_commit_sha=MERGE_SHA
    )
    doc = get(harness, "1")
    assert doc["queue"] is None
    assert doc["state"] == "merged"


def test_the_listing_gives_every_entry_its_position_in_queue_order(harness: Harness) -> None:
    three_annexes(harness)
    harness.githost.set_pull_request_state(2, runs=[GREEN], mergeable_state="behind")
    get(harness, "2")
    doc = listing(harness)
    assert [e["pr_number"] for e in doc["open"]] == [1, 2, 3]
    assert [e["queue"]["position"] for e in doc["open"]] == [1, 2, 3]
    assert all(e["queue"]["of"] == 3 for e in doc["open"])
    # what it waits on, where the service has read it; null says "not read", never "nothing"
    assert [e["queue"]["waiting_on"] for e in doc["open"]] == [None, "branch-update", None]
    assert doc["open"][1]["queue"]["waiting_on_read_at"] is not None
    assert doc["queue"]["order"] == [1, 2, 3]
    assert "not read" in doc["queue"]["note"]


def test_an_entry_is_the_per_id_document_plus_its_queue(harness: Harness) -> None:
    three_annexes(harness)
    [first, *_] = listing(harness)["open"]
    by_id = get(harness, "1")
    assert {k: v for k, v in first.items() if k != "queue"} == by_id["submission"]
    assert first["queue"]["position"] == by_id["queue"]["position"]


def test_the_queue_costs_no_read_per_record(harness: Harness) -> None:
    """The 2026-09-24 rule: nothing here grows with the queue. Twenty-five open, listed five
    times and asked about by id: one listing call, and one pull-request read (the one asked)."""
    token = harness.token_for("code_alice", "alice")
    for _ in range(25):
        annex(harness, token)
    cold(harness)
    for _ in range(5):
        doc = listing(harness)
    assert [e["queue"]["position"] for e in doc["open"]] == list(range(1, 26))
    assert get(harness, "25")["queue"]["position"] == 25
    assert harness.githost.listing_calls == 1
    assert harness.githost.pull_lookups == [25]


def test_a_host_that_cannot_list_says_so_and_keeps_the_last_order(harness: Harness) -> None:
    three_annexes(harness)
    assert get(harness, "3")["queue"]["position"] == 3
    harness.githost.listing_failure = "GET /pulls returned 502"
    age_listing(harness)
    queue = get(harness, "3")["queue"]
    assert queue["position"] == 3 and queue["stale"] is True  # C7: the last order, labelled


def test_no_listing_at_all_is_no_position_not_an_error(harness: Harness) -> None:
    three_annexes(harness)
    harness.githost.listing_failure = "GET /pulls returned 502"
    doc = get(harness, "3")
    assert doc["queue"] == {
        "position": None,
        "of": None,
        "ahead": [],
        "order": doc["queue"]["order"],
        "read_at": None,
        "stale": True,
    }


# --- A13: one name for the artifact type ----------------------------------------------------------


def test_the_record_names_its_artifact_type_as_the_write_routes_do(harness: Harness) -> None:
    proof_record(harness, 7)
    harness.githost.set_pull_request_state(7, head_ref="submit/01M7")
    doc = get(harness, "7")["submission"]
    assert doc.get("artifact_type") == "proof" and doc["kind"] == "proof"
    token = harness.token_for("code_alice", "alice")
    annex(harness, token)
    cold(harness)
    # an annex is not an artifact type of POST /submissions: kind says what it is
    record = get(harness, "1")["submission"]
    assert record["kind"] == "annex" and record.get("artifact_type", "absent") is None
    by_number = {e["pr_number"]: e for e in listing(harness)["open"]}
    assert by_number[7]["artifact_type"] == "proof" and by_number[1]["artifact_type"] is None


# --- A4: a merged pull request is not served as open ----------------------------------------------


def test_a_merge_the_listing_has_seen_is_not_served_as_open(harness: Harness) -> None:
    """The per-pull-request state is cached for 180 s; the open listing, read every 60 s, has
    dropped the pull request. The cached "open" is known to be wrong and is read again."""
    three_annexes(harness)
    harness.githost.set_pull_request_state(1, runs=[GREEN], mergeable_state="clean")
    before = get(harness, "1")
    assert before["pull_request"]["waiting_on"] == "merge"
    harness.githost.set_pull_request_state(
        1, state="closed", merged=True, merge_commit_sha=MERGE_SHA, runs=[GREEN]
    )
    age_listing(harness)  # sixty-one seconds later; the 180 s window has two minutes left
    after = get(harness, "1")
    assert after["pull_request"]["merged"] is True, "served open, stale: false, after the merge"
    assert after["state"] == "merged"
    assert after["pull_request"]["stale"] is False
    assert harness.githost.pull_lookups == [1, 1]  # one re-read, on evidence


def test_a_branch_the_listing_saw_move_is_read_again(harness: Harness) -> None:
    """The actor updated the branch: the listing's head is not the cached one, so the cached
    checks are another commit's (A11: ``merge``, then ``gate`` with nothing saying so)."""
    three_annexes(harness)
    harness.githost.set_pull_request_state(1, runs=[GREEN], mergeable_state="clean")
    assert get(harness, "1")["pull_request"]["waiting_on"] == "merge"
    harness.githost.set_pull_request_state(1, head_sha="b" * 40, runs=[RUNNING])
    age_listing(harness)
    assert get(harness, "1")["pull_request"]["waiting_on"] == "gate"


def test_a_green_pull_request_is_read_again_when_main_moves(harness: Harness) -> None:
    """``main`` moved since a state that said "green" was read: it is the one that merged, or it
    is behind now. The head is asked for once per window by every route already (F05-T13)."""
    three_annexes(harness)
    harness.githost.head = "a" * 40
    frontier.expire(harness.context)  # the service learns where main is
    harness.githost.set_pull_request_state(1, runs=[GREEN], mergeable_state="clean")
    harness.githost.set_pull_request_state(2, runs=[RUNNING])
    assert get(harness, "1")["pull_request"]["waiting_on"] == "merge"
    assert get(harness, "2")["pull_request"]["waiting_on"] == "gate"
    harness.githost.head = "b" * 40
    harness.githost.set_pull_request_state(
        1, state="closed", merged=True, merge_commit_sha="b" * 40, runs=[GREEN]
    )
    frontier.expire(harness.context)  # the head's own window has passed; the listing's has not
    assert get(harness, "1")["state"] == "merged"
    # one whose gate was still running is not re-read for it: main moving says nothing new of it
    assert get(harness, "2")["pull_request"]["waiting_on"] == "gate"
    assert harness.githost.pull_lookups == [1, 2, 1]


def test_an_unchanged_listing_costs_no_second_read(harness: Harness) -> None:
    """The evidence rule re-reads only on evidence: a listing that still carries the pull
    request at the same head leaves the cached state standing for its own window (F07-T47)."""
    three_annexes(harness)
    for _ in range(4):
        get(harness, "1")
        age_listing(harness)
    assert harness.githost.pull_lookups == [1]


def test_a_listing_that_lags_the_merge_costs_one_read_per_window(harness: Harness) -> None:
    """The listing has dropped a pull request the host still calls open (it lags): one re-read
    per listing, never one per request."""
    three_annexes(harness)
    get(harness, "1")
    age_listing(harness)
    listing(harness)
    assert harness.context.open_pulls is not None
    del harness.context.open_pulls.by_number[1]  # the lag
    for _ in range(5):
        assert get(harness, "1")["pull_request"]["state"] == "open"
    assert harness.githost.pull_lookups == [1, 1]


# --- A12: after the merge -------------------------------------------------------------------------


def test_a_merged_proof_waits_on_products_until_it_is_attested(harness: Harness) -> None:
    proof_record(harness, 7)
    harness.githost.set_pull_request_state(
        7, state="closed", merged=True, merge_commit_sha=MERGE_SHA
    )
    doc = get(harness, "7")
    assert doc["attestation_note"] == "attestation-pending"
    assert doc["pull_request"]["waiting_on"] == "products", "null while the post-merge job ran"
    assert doc["state"] == "merged"
    seed_attestation(harness, 7)
    done = get(harness, "7")
    assert done["pull_request"]["waiting_on"] is None and done["attestation"] is not None


def test_a_record_is_closed_at_the_hosts_time_not_the_first_readers(harness: Harness) -> None:
    """#360 merged at 18:19:10Z and was first read at 19:50:21Z; ``closed`` said 19:50:21Z."""
    three_annexes(harness)
    harness.githost.set_pull_request_state(
        1,
        state="closed",
        merged=True,
        merge_commit_sha=MERGE_SHA,
        merged_at="2026-09-09T10:19:10Z",
    )
    harness.clock.advance(hours=3)
    doc = get(harness, "1")
    assert doc["submission"]["closed"] == "2026-09-09T10:19:10Z"
    assert doc["pull_request"]["read_at"] == "2026-09-09T15:00:00Z"  # when it was read stays said


def test_a_pull_request_closed_unmerged_is_closed_at_the_hosts_time_too(harness: Harness) -> None:
    three_annexes(harness)
    harness.githost.set_pull_request_state(2, state="closed", closed_at="2026-09-09T11:00:00Z")
    harness.clock.advance(hours=1)
    doc = get(harness, "2")
    assert doc["submission"]["closed"] == "2026-09-09T11:00:00Z"
    assert doc["state"] == "closed"


# --- the MCP adapter mirrors every field ----------------------------------------------------------


def test_the_tools_carry_the_same_fields_and_pass_their_schemas(harness: Harness) -> None:
    three_annexes(harness)
    client = McpClient(harness)  # validates each result against the tool's schema
    over_http = get(harness, "2")
    assert client.ok("get_submission", {"submission_id": "2"}) == over_http
    assert over_http["queue"]["position"] == 2 and over_http["state"] == "open"
    listed = client.ok("list_submissions", {})
    assert [e["queue"]["position"] for e in listed["open"]] == [1, 2, 3]
    assert listed["queue"]["order"] == [1, 2, 3]
