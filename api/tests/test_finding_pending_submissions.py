"""Finding: a pending submission is invisible through the network (2026-09-13, the Euclid tester).

The tester opened four pull requests through ``POST /submissions`` and then had nothing in the
network to watch them with: ``get_submission`` reads ``attestations/<id>.json``, which exists
only after a merge, so an open pull request — its gate run, its reviews, whether it is blocked —
could only be seen through GitHub's anonymous API, whose budget the tester exhausted (~60 calls).

Mike's decision (2026-09-14, plan decision 2): live pull-request state from the host through the
App (read-only), open work visible on ``get_node``, a ``GET /submissions.json`` snapshot and a
``list_submissions`` tool — no ``frontier/v3`` bump. The service records what it opened
(``store.put_submission``), reads a pull request's state through ``GitHost.get_pull_request``
(cached for ``frontier_max_stale_s`` in ``Context.pulls``, the last state served on a host
failure with ``pull_request_error`` set, C7), and ``GET /submissions/{id}`` answers by the
submission's ULID or the pull-request number, padded or not, with the attestation linked once
one exists. Service side is F07-T16; the MCP side (``get_submission`` = the route,
``get_node.submissions``, ``list_submissions``) is F09-T7.

Every new symbol (store methods, the fake host's ``set_pull_request_state``, ``pull_lookups``,
``pr_lookup_failure``, the routes, the tool) is looked up inside the test body, never imported:
a collection error is not an xfail. Each test is a strict xfail until its task lands
(conventions §2).
"""

from __future__ import annotations

import dataclasses
import json
import time
from typing import Any

import pytest
import samples
from api_fakes import (
    PROOF_PREFIX,
    TUTORIAL_NODE,
    TUTORIAL_PROOF,
    Harness,
    PrecheckKey,
    make_harness,
    make_precheck_key,
)
from mcp_client import NODE, McpClient, plain, seed_node

from opn_api import clock as clockmod

TARGET = "propositional"
PROOF_PATH = f"{PROOF_PREFIX}{TUTORIAL_NODE}/Proof.lean"
UNKNOWN_ULID = "01M00000000000000000000000"
MERGE_SHA = "7" * 40
HEAD_SHA = "6" * 40
FAILED_GATE = {
    "name": "gate",
    "status": "completed",
    "conclusion": "failure",
    "url": "https://github.com/runs/1",
}
REVIEW = {"login": "bob", "state": "COMMENTED"}
SUBMISSION_FIELDS = {
    "id",
    "node_id",
    "target_id",
    "kind",
    "pr_number",
    "pr_url",
    "pseudonym",
    "precheck_job_id",
    "created",
}
SERVICE = (
    "finding pending-submissions (F07-R1, F07-R11, D-28, C7): {}; fix: F07-T16 (Mike, 2026-09-14)"
)
MCP = "finding pending-submissions (F09-R5, D-28): {}; fix: F09-T7 (Mike, 2026-09-14)"


@pytest.fixture(scope="module")
def key(tmp_path_factory: pytest.TempPathFactory) -> PrecheckKey:
    return make_precheck_key(tmp_path_factory.mktemp("precheck-key"))


# --- helpers --------------------------------------------------------------------------------------


def submit_proof(
    h: Harness, key: PrecheckKey, token: str, node: str = TUTORIAL_NODE
) -> dict[str, Any]:
    """A passing precheck by the token's identity, then ``POST /submissions`` on it — the
    node's proof, as ``test_submissions.test_submission_opens_pr`` drives it."""
    job = h.tutorial_job(key, node=node, token=token)
    r = h.client.post(
        "/submissions",
        json={
            "node_id": node,
            "artifact_type": "proof",
            "bundle": {f"{PROOF_PREFIX}{node}/Proof.lean": TUTORIAL_PROOF},
            "precheck_job_id": job["id"],
        },
        headers=h.auth(token),
    )
    assert r.status_code == 201, r.text  # guard: the submission itself opens today
    doc: dict[str, Any] = r.json()
    doc["precheck_job_id"] = job["id"]
    return doc


def submit_annex(h: Harness, token: str) -> dict[str, Any]:
    r = h.client.post(
        "/annexes",
        json={"node_id": TUTORIAL_NODE, "text": "Both conjuncts are already in hand.\n"},
        headers=h.auth(token),
    )
    assert r.status_code == 201, r.text  # guard
    doc: dict[str, Any] = r.json()
    return doc


def as_dict(record: Any) -> dict[str, Any]:
    """A store record as a mapping, whether the store answers a dataclass or a dict."""
    if dataclasses.is_dataclass(record) and not isinstance(record, type):
        return dataclasses.asdict(record)
    assert isinstance(record, dict), f"a submission record, not {record!r}"
    return record


def state_setter(h: Harness) -> Any:
    """The fake host's seeding hook for a pull request's live state (F07-T16). Its absence is
    the red reason of every test that needs a pull request in a given state."""
    setter = getattr(h.githost, "set_pull_request_state", None)
    assert callable(setter), "FakeGitHost.set_pull_request_state does not exist (F07-T16)"
    return setter


def lookups(h: Harness) -> int:
    """How many times the service asked the host for a pull request's state."""
    seen = getattr(h.githost, "pull_lookups", None)
    assert seen is not None, "FakeGitHost.pull_lookups does not exist (F07-T16)"
    return len(seen)


def age_pull_cache(h: Harness) -> None:
    """``test_frontier.force_stale`` for the pull-request cache: every entry in
    ``Context.pulls`` was fetched a window and a second ago, on the monotonic clock."""
    window = h.settings.frontier_max_stale_s
    for entry in getattr(h.context, "pulls", {}).values():
        entry.fetched_at = time.monotonic() - (window + 1)


def json_of(r: Any) -> dict[str, Any]:
    """The response body as an object; a non-JSON body (Starlette's own 404 for a route that
    does not exist) becomes ``{}`` so the assertion names the missing route, not a decode."""
    try:
        doc = r.json()
    except ValueError:
        return {}
    return doc if isinstance(doc, dict) else {}


def get_submission(h: Harness, submission_id: str) -> dict[str, Any]:
    r = h.client.get(f"/submissions/{submission_id}")
    assert r.status_code == 200, f"GET /submissions/{submission_id}: {r.status_code} {r.text}"
    return json_of(r)


def seed_attestation(h: Harness, number: int) -> str:
    path = f"attestations/{number:06d}.json"
    h.githost.files[path] = json.dumps(
        samples.attestation(node_id=TUTORIAL_NODE, graph_commit="5" * 40)
    ).encode()
    h.context.files.clear()
    return path


# --- F07-T16: the record --------------------------------------------------------------------------


def test_post_submissions_records_the_submission(harness: Harness, key: PrecheckKey) -> None:
    """The store keeps ``{id, node_id, target_id, kind, pr_number, pr_url, pseudonym,
    precheck_job_id, created}`` for the pull request the service opened, reachable by id and
    by pull-request number, and open until a live read finds it finished."""
    token = harness.token_for("code_alice", "alice")
    opened = submit_proof(harness, key, token)
    get = getattr(harness.store, "get_submission", None)
    assert callable(get), "Store.get_submission does not exist"

    record = as_dict(get(opened["submission_id"]))
    assert set(record) >= SUBMISSION_FIELDS, sorted(record)
    assert {k: record[k] for k in SUBMISSION_FIELDS} == {
        "id": opened["submission_id"],
        "node_id": TUTORIAL_NODE,
        "target_id": TARGET,
        "kind": "proof",
        "pr_number": 1,
        "pr_url": opened["pr_url"],
        "pseudonym": "alice",
        "precheck_job_id": opened["precheck_job_id"],
        "created": clockmod.render(harness.clock.now()),
    }
    by_pr = getattr(harness.store, "get_submission_by_pr", None)
    assert callable(by_pr), "Store.get_submission_by_pr does not exist"
    assert as_dict(by_pr(1)) == record
    open_ones = getattr(harness.store, "list_open_submissions", None)
    assert callable(open_ones), "Store.list_open_submissions does not exist"
    assert [as_dict(r)["id"] for r in open_ones()] == [opened["submission_id"]]


# --- F07-T16: GET /submissions/{id} ---------------------------------------------------------------


def test_get_submission_by_ulid_or_pr_number_answers_the_live_pull_request(
    harness: Harness, key: PrecheckKey
) -> None:
    """The ULID, ``1`` and ``000001`` are the same answer; an open pull request whose gate
    failed carries that run, its reviews and ``mergeable_state``, and no attestation yet."""
    set_state = state_setter(harness)
    token = harness.token_for("code_alice", "alice")
    opened = submit_proof(harness, key, token)
    set_state(
        1,
        state="open",
        merged=False,
        mergeable_state="blocked",
        head_sha=HEAD_SHA,
        runs=[FAILED_GATE],
        reviews=[REVIEW],
    )

    by_ulid = get_submission(harness, opened["submission_id"])
    assert get_submission(harness, "1") == by_ulid
    assert get_submission(harness, "000001") == by_ulid

    assert set(by_ulid) >= {
        "submission",
        "pull_request",
        "pull_request_error",
        "attestation_path",
        "attestation",
        "attestation_note",
    }, sorted(by_ulid)
    assert by_ulid["submission"]["id"] == opened["submission_id"]
    assert by_ulid["submission"]["pr_number"] == 1
    pr = by_ulid["pull_request"]
    assert pr["state"] == "open"
    assert pr["merged"] is False
    assert pr["mergeable_state"] == "blocked"
    assert pr["url"] == opened["pr_url"]
    assert pr["runs"][0]["name"] == "gate"
    assert pr["runs"][0]["conclusion"] == "failure"
    assert pr["reviews"] == [REVIEW]
    assert by_ulid["pull_request_error"] is None
    assert by_ulid["attestation_path"] is None
    assert by_ulid["attestation"] is None
    assert by_ulid["attestation_note"] == "not-merged"


def test_a_merged_proof_links_its_attestation_and_is_never_looked_up_again(
    harness: Harness, key: PrecheckKey
) -> None:
    """Merged, with ``attestations/000001.json`` committed: the answer names the path and
    carries the file as the graph holds it; the record is closed, so a cold service (a fresh
    context over the same store and host) answers the same without asking the host."""
    set_state = state_setter(harness)
    token = harness.token_for("code_alice", "alice")
    opened = submit_proof(harness, key, token)
    set_state(
        1,
        state="closed",
        merged=True,
        mergeable_state="unknown",
        head_sha=HEAD_SHA,
        merge_commit_sha=MERGE_SHA,
        runs=[{**FAILED_GATE, "conclusion": "success"}],
        reviews=[],
    )
    path = seed_attestation(harness, 1)

    doc = get_submission(harness, "1")
    assert doc["pull_request"]["merged"] is True
    assert doc["attestation_path"] == path
    assert doc["attestation"] == plain(harness, path)
    assert doc["attestation_note"] is None

    open_ones = getattr(harness.store, "list_open_submissions", None)
    assert callable(open_ones), "Store.list_open_submissions does not exist"
    assert opened["submission_id"] not in [as_dict(r)["id"] for r in open_ones()]

    before = lookups(harness)
    cold = make_harness(store=harness.store, githost=harness.githost, clock=harness.clock)
    with cold.client:
        again = get_submission(cold, "1")
    assert lookups(harness) == before, "a closed submission asked the host again"
    assert again == doc


def test_a_merged_annex_answers_no_attestation_for_mode(harness: Harness) -> None:
    """The append routes record what they open too (kind ``annex``); a merged append answers
    ``attestation_note: no-attestation-for-mode`` — the half ``test_finding_submission_ids.py``
    declined for want of a seam that ties a pull-request number to its mode."""
    set_state = state_setter(harness)
    token = harness.token_for("code_alice", "alice")
    opened = submit_annex(harness, token)
    set_state(1, state="closed", merged=True, merge_commit_sha=MERGE_SHA, runs=[], reviews=[])

    doc = get_submission(harness, "1")
    assert doc["submission"]["id"] == opened["id"]
    assert doc["submission"]["kind"] == "annex"
    assert doc["submission"]["pr_number"] == opened["pr_number"] == 1
    assert doc["attestation_path"] is None
    assert doc["attestation"] is None
    assert doc["attestation_note"] == "no-attestation-for-mode"


def test_unknown_is_404_and_a_hand_opened_pull_request_answers_without_a_record(
    harness: Harness,
) -> None:
    """An id the service never opened and the graph never attested is ``404
    submission-unknown``; a hand-opened pull request whose merge wrote an attestation answers
    200 with ``submission: null`` and the attestation."""
    for unknown in (UNKNOWN_ULID, "999", "000999"):
        r = harness.client.get(f"/submissions/{unknown}")
        assert r.status_code == 404, (unknown, r.status_code, r.text)
        assert json_of(r).get("error") == "submission-unknown", (unknown, r.text)

    set_state = state_setter(harness)
    set_state(33, state="closed", merged=True, merge_commit_sha=MERGE_SHA, runs=[], reviews=[])
    path = seed_attestation(harness, 33)
    doc = get_submission(harness, "33")
    assert doc["submission"] is None
    assert doc["attestation_path"] == path
    assert doc["attestation"] == plain(harness, path)
    assert get_submission(harness, "000033") == doc


def test_the_pull_request_state_is_cached_and_survives_a_host_failure(
    harness: Harness, key: PrecheckKey
) -> None:
    """Two reads inside the window are one host lookup; once the window has passed a read looks
    again; when that lookup fails the last state is served with ``pull_request_error`` set (C7),
    never a 5xx and never a silent success."""
    set_state = state_setter(harness)
    token = harness.token_for("code_alice", "alice")
    submit_proof(harness, key, token)
    set_state(1, state="open", merged=False, mergeable_state="blocked", runs=[FAILED_GATE])

    first = get_submission(harness, "1")
    assert get_submission(harness, "1") == first
    assert lookups(harness) == 1

    age_pull_cache(harness)
    assert getattr(harness.context, "pulls", None), "Context.pulls holds no cached state"
    set_state(1, state="open", merged=False, mergeable_state="clean", runs=[])
    fresh = get_submission(harness, "1")
    assert lookups(harness) == 2
    assert fresh["pull_request"]["mergeable_state"] == "clean"

    age_pull_cache(harness)
    assert hasattr(harness.githost, "pr_lookup_failure"), "FakeGitHost.pr_lookup_failure"
    harness.githost.pr_lookup_failure = "GET /repos/.../pulls/1 returned 502"
    served = get_submission(harness, "1")
    assert served["pull_request"] == fresh["pull_request"], "the last good state is served"
    assert isinstance(served["pull_request_error"], str) and served["pull_request_error"]


def test_submissions_json_lists_open_work_and_drops_the_merged(
    harness: Harness, key: PrecheckKey
) -> None:
    """``{snapshot_at, open: [...]}``: every open record, each the ``submission`` document
    ``GET /submissions/{id}`` carries; a submission a live read found merged is gone."""
    set_state = state_setter(harness)
    token = harness.token_for("code_alice", "alice")
    proof = submit_proof(harness, key, token)
    annex = submit_annex(harness, token)
    set_state(1, state="open", merged=False, runs=[], reviews=[])
    set_state(2, state="open", merged=False, runs=[], reviews=[])

    r = harness.client.get("/submissions.json")
    assert r.status_code == 200, f"GET /submissions.json: {r.status_code} {r.text}"
    snapshot = json_of(r)
    assert set(snapshot) == {"snapshot_at", "open"}, sorted(snapshot)
    assert snapshot["snapshot_at"] == clockmod.render(harness.clock.now())
    assert sorted(e["pr_number"] for e in snapshot["open"]) == [1, 2]
    assert {e["id"] for e in snapshot["open"]} == {proof["submission_id"], annex["id"]}

    set_state(1, state="closed", merged=True, merge_commit_sha=MERGE_SHA, runs=[], reviews=[])
    age_pull_cache(harness)
    assert get_submission(harness, "1")["pull_request"]["merged"] is True

    after = json_of(harness.client.get("/submissions.json"))
    assert [e["pr_number"] for e in after["open"]] == [2]
    assert after["open"][0] == get_submission(harness, "2")["submission"]


# --- F09-T7: the MCP side -------------------------------------------------------------------------


def test_get_node_lists_the_open_submissions_on_the_node(
    harness: Harness, key: PrecheckKey
) -> None:
    """``get_node(...)["submissions"]["open"]`` is the open records for that node, and only
    that node's: a submission on the tutorial node does not appear on ``and-reassoc``."""
    seed_node(harness)  # the fixture node's files, so get_node answers (mcp_client)
    token = harness.token_for("code_alice", "alice")
    opened = submit_proof(harness, key, token, node=NODE)
    submit_proof(harness, key, token)  # PR 2, on the tutorial node

    doc = McpClient(harness).ok("get_node", {"node_id": NODE})
    assert "submissions" in doc, sorted(doc)
    [entry] = doc["submissions"]["open"]
    assert entry["pr_number"] == 1
    assert entry["id"] == opened["submission_id"]
    assert entry["node_id"] == NODE


def test_get_submission_tool_equals_the_route(harness: Harness, key: PrecheckKey) -> None:
    """The tool is ``GET /submissions/{submission_id}``, body for body."""
    set_state = state_setter(harness)
    token = harness.token_for("code_alice", "alice")
    submit_proof(harness, key, token)
    set_state(1, state="open", merged=False, mergeable_state="blocked", runs=[FAILED_GATE])

    over_http = get_submission(harness, "1")
    over_mcp = McpClient(harness).ok("get_submission", {"submission_id": "1"})
    assert over_mcp == over_http


@pytest.mark.xfail(
    strict=True,
    reason=MCP.format(
        "list_submissions is built (reads.list_submissions) but not registered as a tool; "
        "the MCP adapter's registration is another agent's work (2026-09-14)"
    ),
)
def test_list_submissions_is_a_tool_and_equals_the_snapshot(
    harness: Harness, key: PrecheckKey
) -> None:
    """``list_submissions`` is a read (no bearer) listed in ``tools/list``, and its result is
    ``GET /submissions.json``."""
    token = harness.token_for("code_alice", "alice")
    submit_proof(harness, key, token)
    client = McpClient(harness)
    names = {t.name for t in client.list_tools()}
    assert "list_submissions" in names, sorted(names)

    over_mcp = client.ok("list_submissions")
    r = harness.client.get("/submissions.json")
    assert r.status_code == 200, r.text
    assert over_mcp == r.json()
    assert [e["pr_number"] for e in over_mcp["open"]] == [1]
