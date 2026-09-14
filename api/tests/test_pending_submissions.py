"""F07-T16: pending submissions — the record, the live state, the cache, the routes.

``test_finding_pending_submissions.py`` is the specification and drives ``POST /submissions``,
whose record call waits on another session's commit. The same behaviours are driven here through
the routes that record today (the append routes and the proposals), plus the edge cases the
specification does not reach: a host failure on the first read ever, a pull request closed
unmerged, a number the host no longer knows, ids padded past six digits, a malformed id, a store
failure while recording, the merged-but-not-yet-attested window, and the two stores' parity.
The MCP side is ``test_mcp_pending_submissions.py`` (F09-T7).
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import replace
from typing import Any

import pytest
import samples
from api_fakes import TUTORIAL_NODE, Harness, make_harness
from mcp_client import plain
from test_store_seam import dynamo

from opn_api import clock as clockmod
from opn_api import pending, submissions
from opn_api.store import MemoryStore, Store, Submission

TARGET = "propositional"
MERGE_SHA = "7" * 40
FAILED_GATE = {"name": "gate", "status": "completed", "conclusion": "failure", "url": "u"}


def annex(h: Harness, token: str, node: str = TUTORIAL_NODE) -> dict[str, Any]:
    r = h.client.post(
        "/annexes", json={"node_id": node, "text": "An informal argument.\n"}, headers=h.auth(token)
    )
    assert r.status_code == 201, r.text
    doc: dict[str, Any] = r.json()
    return doc


def get(h: Harness, submission_id: str) -> dict[str, Any]:
    r = h.client.get(f"/submissions/{submission_id}")
    assert r.status_code == 200, (submission_id, r.status_code, r.text)
    doc: dict[str, Any] = r.json()
    return doc


def age(h: Harness) -> None:
    """Every cached pull request fetched a window and a second ago, relative to now (the
    monotonic clock counts from boot, so an epoch of 0.0 can still be fresh)."""
    window = h.settings.frontier_max_stale_s
    for entry in h.context.pulls.values():
        entry.fetched_at = time.monotonic() - (window + 1)


def proof_record(h: Harness, number: int = 7) -> Submission:
    """A proof record put straight into the store — ``POST /submissions`` does not record yet
    (its call lands with the other session's commit), and the attesting branches need one."""
    record = Submission(
        id="01M00000000000000000000007",
        kind="proof",
        node_id=TUTORIAL_NODE,
        target_id=TARGET,
        pr_number=number,
        pr_url=f"https://github.com/pr/{number}",
        pseudonym="alice",
        precheck_job_id="01M00000000000000000000009",
        created=clockmod.render(h.clock.now()),
    )
    h.store.put_submission(record)
    return record


def seed_attestation(h: Harness, number: int) -> str:
    path = pending.attestation_path(number)
    h.githost.files[path] = json.dumps(
        samples.attestation(node_id=TUTORIAL_NODE, graph_commit="5" * 40)
    ).encode()
    h.context.files.clear()
    return path


# --- the record, from every route that records today ----------------------------------------------


def test_the_append_routes_record_what_they_open(harness: Harness) -> None:
    """Each route's pull request is recorded under the id it answered, with its kind."""
    token = harness.token_for("code_alice", "alice")
    opened = annex(harness, token)
    postmortem = harness.client.post(
        "/postmortems",
        json={"node_id": TUTORIAL_NODE, "yaml": samples.postmortem(node=TUTORIAL_NODE)},
        headers=harness.auth(token),
    )
    assert postmortem.status_code == 201, postmortem.text
    approach = harness.client.post(
        "/approach-records",
        json={"target_id": TARGET, "record": {"route": "normalise", "outcome": "exhausted"}},
        headers=harness.auth(token),
    )
    assert approach.status_code == 201, approach.text

    records = {s.pr_number: s for s in harness.store.list_open_submissions()}
    assert {n: (s.kind, s.node_id, s.id) for n, s in records.items()} == {
        1: ("annex", TUTORIAL_NODE, opened["id"]),
        2: ("postmortem", TUTORIAL_NODE, postmortem.json()["id"]),
        3: ("approach-record", None, approach.json()["id"]),
    }
    for number, record in records.items():
        assert record.target_id == TARGET
        assert record.pseudonym == "alice"
        assert record.precheck_job_id is None
        assert record.pr_url == f"https://github.com/{harness.settings.graph_repo}/pull/{number}"
        assert record.created == clockmod.render(harness.clock.now())
        assert record.closed is None
        assert harness.store.get_submission_by_pr(number) == record


def test_a_witness_proposal_is_recorded_as_a_witness(harness: Harness) -> None:
    graph_path = f"targets/{TARGET}/graph.json"
    doc = json.loads(harness.githost.files[graph_path])
    hole = {**doc["nodes"][0], "node_id": "and-reassoc--h1"}
    doc["nodes"].append({**hole, "status": "blocked", "cause": "witness-missing"})
    harness.githost.files[graph_path] = json.dumps(doc).encode()
    harness.context.files.clear()
    token = harness.token_for("code_alice", "alice")
    r = harness.client.post(
        "/proposals/witness",
        json={"node_id": "and-reassoc--h1", "witness": "theorem witness : True := trivial\n"},
        headers=harness.auth(token),
    )
    assert r.status_code == 201, r.text
    record = harness.store.get_submission(r.json()["proposal_id"])
    assert record is not None
    assert (record.kind, record.node_id, record.pr_number) == ("witness", "and-reassoc--h1", 1)
    assert get(harness, "1")["attestation_note"] == "no-attestation-for-mode"


def test_a_store_failure_while_recording_still_answers_201(
    harness: Harness, caplog: pytest.LogCaptureFixture
) -> None:
    """The pull request is open whatever the store does: the caller gets its number, and the
    lost record is logged at ERROR (C7), never a 500 over a pull request that exists."""
    token = harness.token_for("code_alice", "alice")

    def refuse(submission: Submission) -> None:
        raise RuntimeError

    harness.store.put_submission = refuse  # type: ignore[method-assign]
    with caplog.at_level(logging.ERROR, logger="opn_api.pending"):
        opened = annex(harness, token)
    assert opened["pr_number"] == 1
    assert any("not recorded" in r.getMessage() for r in caplog.records)


def test_attesting_kinds_are_the_submission_artifact_types() -> None:
    """Held equal rather than imported, because submissions will import pending."""
    assert pending.ATTESTING_KINDS == submissions.ARTIFACT_TYPES


# --- GET /submissions/{id}: ids -------------------------------------------------------------------


@pytest.mark.parametrize("spelling", ["1", "000001", "0000000001", "{ulid}", "{ulid_lower}"])
def test_every_spelling_of_the_id_is_the_same_answer(harness: Harness, spelling: str) -> None:
    token = harness.token_for("code_alice", "alice")
    opened = annex(harness, token)
    wanted = get(harness, opened["id"])
    submission_id = spelling.format(ulid=opened["id"], ulid_lower=opened["id"].lower())
    assert get(harness, submission_id) == wanted
    assert wanted["submission"]["id"] == opened["id"]


@pytest.mark.parametrize("raw", ["0", "000000", "1" + "0" * 12])
def test_numbers_that_name_nothing_are_unknown_without_a_host_lookup(
    harness: Harness, raw: str
) -> None:
    """Zero, and a number past any pull request, answer 404 and ask the host nothing."""
    r = harness.client.get(f"/submissions/{raw}")
    assert (r.status_code, r.json()["error"]) == (404, "submission-unknown")
    assert harness.githost.pull_lookups == []


@pytest.mark.parametrize("raw", ["not-an-id", "01M0000000000000000000000U"])
def test_a_malformed_id_is_refused_by_name(harness: Harness, raw: str) -> None:
    """Neither digits nor a ULID — the second has ``U``, which Crockford base32 leaves out."""
    r = harness.client.get(f"/submissions/{raw}")
    assert (r.status_code, r.json()["error"]) == (400, "submission-id-invalid")
    assert harness.githost.pull_lookups == []


# --- the live state and the cache (C7) ------------------------------------------------------------


def test_reads_inside_the_window_are_one_lookup_and_a_failure_serves_the_last_state(
    harness: Harness,
) -> None:
    token = harness.token_for("code_alice", "alice")
    annex(harness, token)
    harness.githost.set_pull_request_state(1, mergeable_state="blocked", runs=[FAILED_GATE])
    first = get(harness, "1")
    assert get(harness, "1") == first
    assert harness.githost.pull_lookups == [1]
    assert first["pull_request"]["runs"] == [FAILED_GATE]
    assert first["pull_request_error"] is None

    age(harness)
    harness.githost.set_pull_request_state(1, mergeable_state="clean")
    assert get(harness, "1")["pull_request"]["mergeable_state"] == "clean"
    assert harness.githost.pull_lookups == [1, 1]

    age(harness)
    harness.githost.pr_lookup_failure = "GET /repos/o/g/pulls/1 returned 502"
    served = get(harness, "1")
    assert served["pull_request"]["mergeable_state"] == "clean"
    assert "502" in served["pull_request_error"]
    assert harness.store.list_open_submissions()[0].closed is None  # an outage closes nothing
    harness.githost.pr_lookup_failure = None
    assert get(harness, "1")["pull_request_error"] is None  # the next read retries at once


def test_a_host_failure_on_the_first_read_ever_is_a_null_state_with_the_error(
    harness: Harness,
) -> None:
    """No last state to serve: ``pull_request`` is null and the error says why; a proof whose
    state is unknown and has no attestation on main says so rather than ``not-merged``."""
    token = harness.token_for("code_alice", "alice")
    annex(harness, token)
    proof_record(harness)
    harness.githost.pr_lookup_failure = "GET /repos/o/g/pulls/1 failed: ConnectError"
    doc = get(harness, "1")
    assert doc["pull_request"] is None
    assert "ConnectError" in doc["pull_request_error"]
    assert doc["attestation_note"] == "no-attestation-for-mode"
    proof = get(harness, "7")
    assert (proof["pull_request"], proof["attestation"]) == (None, None)
    assert proof["attestation_note"] == "pull-request-unavailable"


def test_a_number_the_host_does_not_know_is_a_null_state_with_the_error(harness: Harness) -> None:
    proof_record(harness, number=40)
    doc = get(harness, "40")
    assert doc["pull_request"] is None
    assert doc["pull_request_error"] == (
        f"the host has no pull request #40 on {harness.settings.graph_repo}"
    )
    assert doc["submission"]["closed"] is None
    assert get(harness, "40") == doc
    assert harness.githost.pull_lookups == [40]  # the absence is cached for the window too


# --- finishing ------------------------------------------------------------------------------------


def test_a_pull_request_closed_unmerged_closes_the_record(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice")
    annex(harness, token)
    proof_record(harness)
    harness.githost.set_pull_request_state(7, state="closed", merged=False)
    doc = get(harness, "7")
    assert doc["pull_request"]["state"] == "closed"
    assert doc["attestation_note"] == "not-merged"
    assert doc["submission"]["closed"] == clockmod.render(harness.clock.now())
    assert [s.pr_number for s in harness.store.list_open_submissions()] == [1]
    snapshot = harness.client.get("/submissions.json").json()
    assert [e["pr_number"] for e in snapshot["open"]] == [1]

    cold = make_harness(store=harness.store, githost=harness.githost, clock=harness.clock)
    before = list(harness.githost.pull_lookups)
    assert get(cold, "7") == doc
    assert harness.githost.pull_lookups == before


def test_a_merged_proof_is_pending_until_its_attestation_lands(harness: Harness) -> None:
    """Between the merge and the post-merge job's commit the answer says the attestation is on
    its way; once the file is on main it is the answer, with no further host call."""
    record = proof_record(harness)
    harness.githost.set_pull_request_state(
        7, state="closed", merged=True, merge_commit_sha=MERGE_SHA
    )
    waiting = get(harness, "7")
    assert (waiting["attestation"], waiting["attestation_note"]) == (None, "attestation-pending")
    assert waiting["submission"]["closed"] is not None
    assert harness.store.list_open_submissions() == []

    path = seed_attestation(harness, 7)
    lookups = list(harness.githost.pull_lookups)
    landed = get(harness, record.id)
    assert landed["attestation_path"] == path == "attestations/000007.json"
    assert landed["attestation"] == plain(harness, path)
    assert landed["attestation_note"] is None
    assert landed["pull_request"] == waiting["pull_request"]
    assert harness.githost.pull_lookups == lookups


def test_a_merged_annex_leaves_the_snapshot(harness: Harness) -> None:
    token = harness.token_for("code_alice", "alice")
    annex(harness, token)
    annex(harness, token)
    first = harness.client.get("/submissions.json").json()
    assert set(first) == {"snapshot_at", "open"}
    assert first["snapshot_at"] == clockmod.render(harness.clock.now())
    assert [e["pr_number"] for e in first["open"]] == [1, 2]

    harness.githost.set_pull_request_state(1, state="closed", merged=True)
    assert get(harness, "1")["submission"]["closed"] is not None
    snapshot = harness.client.get("/submissions.json").json()
    assert [e["pr_number"] for e in snapshot["open"]] == [2]
    assert snapshot["open"][0] == get(harness, "2")["submission"]


# --- the store seam: both halves agree ------------------------------------------------------------


@pytest.fixture(params=["memory", "dynamodb"])
def store(request: pytest.FixtureRequest) -> Store:
    return MemoryStore() if request.param == "memory" else dynamo()


def record(number: int, **overrides: Any) -> Submission:
    base = Submission(
        id=f"01M{number:023d}",
        kind="annex",
        node_id=None if number % 2 else TUTORIAL_NODE,
        target_id=TARGET,
        pr_number=number,
        pr_url=f"https://github.com/pr/{number}",
        pseudonym="alice",
        precheck_job_id=None,
        created="2026-09-14T12:00:00Z",
    )
    return replace(base, **overrides)


def test_submissions_round_trip_in_both_stores(store: Store) -> None:
    first, second = record(1), record(2, kind="proof", precheck_job_id="01MJOB")
    store.put_submission(second)
    store.put_submission(first)
    assert store.get_submission(first.id) == first
    assert store.get_submission_by_pr(2) == second
    assert store.get_submission("01MNOPE") is None
    assert store.get_submission_by_pr(99) is None
    assert store.list_open_submissions() == [first, second]


def test_closing_keeps_the_final_state_and_leaves_the_open_index_in_both_stores(
    store: Store,
) -> None:
    store.put_submission(record(1))
    store.put_submission(record(2))
    final = {"state": "closed", "merged": True, "runs": [FAILED_GATE], "reviews": [], "number": 1}
    closed = store.close_submission(record(1).id, closed="2026-09-14T13:00:00Z", final_state=final)
    assert closed == record(1, closed="2026-09-14T13:00:00Z", final_state=final)
    assert store.get_submission_by_pr(1) == closed
    assert store.list_open_submissions() == [record(2)]
    store.close_submission(record(2).id, closed="2026-09-14T13:00:01Z", final_state=final)
    assert store.list_open_submissions() == []  # the last id out empties the set
    assert store.close_submission("01MNOPE", closed="x", final_state=final) is None
    store.put_submission(record(3))
    assert [s.pr_number for s in store.list_open_submissions()] == [3]


def test_the_dynamo_layout_is_three_prefixes_in_the_tokens_table_without_a_ttl() -> None:
    table_store = dynamo()
    table_store.put_submission(record(4))
    table = table_store._tokens
    assert set(table.items) == {
        "submission#01M00000000000000000000004",
        "submissionpr#4",
        "submissions#open",
    }
    assert all("expires_at" not in item for item in table.items.values())
    assert table.items["submissions#open"]["ids"] == {"01M00000000000000000000004"}
