"""Finding: ``GET /submissions.json`` lists merged pull requests as open, for ever.

Found 2026-09-16, orchestrating the Erdős 412 live run. The tester reported "four pull requests
open since 2026-09-14" and read it as slow humans; #66-#69 had in fact merged on 2026-09-15.

The mechanism: reconciliation is lazy *and per-submission*. ``pending.answer()`` — the
``GET /submissions/{id}`` route — does a ``live_state`` read and calls ``store.close_submission``
for the one id it was handed. ``pending.snapshot()`` renders ``store.list_open_submissions()``
with no live read at all. So a submission stays "open" until somebody happens to ask about it
*individually*; nobody ever does, and the list is wrong for ever. Proven live: the open list read
``[66, 67, 68, 69, 70, 71]``, one ``get_submission("66")`` dropped 66, and the rest stayed.

The existing coverage could not see it. ``test_finding_pending_submissions``'s
``test_submissions_json_lists_open_work_and_drops_the_merged`` asserts the drop, but it calls
``get_submission(harness, "1")`` on the line before — the per-submission read is what closes the
record, so the test passes today and pins the defect rather than catching it. These tests never
read a submission individually: the snapshot must reconcile on its own.

Fix: one ``reconcile`` helper, used by both the route and the snapshot.
"""

from __future__ import annotations

import time
from typing import Any

import pytest
from api_fakes import (
    PROOF_PREFIX,
    TUTORIAL_NODE,
    TUTORIAL_PROOF,
    Harness,
    PrecheckKey,
    make_precheck_key,
)
from mcp_client import McpClient

MERGE_SHA = "7" * 40
FINDING = (
    "finding stale-open-submissions (F07-R11, C7): {}; "
    "fix: pending.reconcile shared by the route and the snapshot (2026-09-16)"
)


@pytest.fixture(scope="module")
def key(tmp_path_factory: pytest.TempPathFactory) -> PrecheckKey:
    return make_precheck_key(tmp_path_factory.mktemp("precheck-key"))


# --- helpers (deliberately not imported from the F07 finding module: no per-submission read) ------


def submit_proof(h: Harness, key: PrecheckKey, token: str) -> dict[str, Any]:
    job = h.tutorial_job(key, node=TUTORIAL_NODE, token=token)
    r = h.client.post(
        "/submissions",
        json={
            "node_id": TUTORIAL_NODE,
            "artifact_type": "proof",
            "bundle": {f"{PROOF_PREFIX}{TUTORIAL_NODE}/Proof.lean": TUTORIAL_PROOF},
            "precheck_job_id": job["id"],
        },
        headers=h.auth(token),
    )
    assert r.status_code == 201, r.text  # guard
    doc: dict[str, Any] = r.json()
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


def state_setter(h: Harness) -> Any:
    setter = getattr(h.githost, "set_pull_request_state", None)
    assert callable(setter), "FakeGitHost.set_pull_request_state does not exist"
    return setter


def age_pull_cache(h: Harness) -> None:
    """Every cached pull-request state was fetched a window and a second ago (F05-T10's rule:
    force staleness from *now*, never by assuming the monotonic clock's origin)."""
    window = h.settings.frontier_max_stale_s
    for entry in getattr(h.context, "pulls", {}).values():
        entry.fetched_at = time.monotonic() - (window + 1)


def lookups(h: Harness) -> int:
    seen = getattr(h.githost, "pull_lookups", None)
    assert seen is not None, "FakeGitHost.pull_lookups does not exist"
    return len(seen)


def snapshot(h: Harness) -> dict[str, Any]:
    r = h.client.get("/submissions.json")
    assert r.status_code == 200, f"GET /submissions.json: {r.status_code} {r.text}"
    doc: dict[str, Any] = r.json()
    return doc


def open_numbers(h: Harness) -> list[int]:
    return sorted(e["pr_number"] for e in snapshot(h)["open"])


# --- the finding ----------------------------------------------------------------------------------


def test_the_snapshot_drops_a_merged_pull_request_nobody_asked_about(
    harness: Harness, key: PrecheckKey
) -> None:
    """The live case: two submissions, one merges, and the only reader is the list itself.

    Nothing here calls ``GET /submissions/{id}``. That is the whole point — on the live service
    #66-#69 sat in this list for two days precisely because no one did.
    """
    set_state = state_setter(harness)
    token = harness.token_for("code_alice", "alice")
    submit_proof(harness, key, token)  # PR 1
    submit_annex(harness, token)  # PR 2
    set_state(1, state="open", merged=False, runs=[], reviews=[])
    set_state(2, state="open", merged=False, runs=[], reviews=[])
    assert open_numbers(harness) == [1, 2]  # guard: both are open to start with

    set_state(1, state="closed", merged=True, merge_commit_sha=MERGE_SHA, runs=[], reviews=[])
    age_pull_cache(harness)

    assert open_numbers(harness) == [2], FINDING.format(
        "a merged pull request is still listed open by GET /submissions.json"
    )


def test_the_snapshot_closes_the_record_not_just_the_view(
    harness: Harness, key: PrecheckKey
) -> None:
    """Reconciling is a write to the store, so the next reader — and a cold service over the
    same store — sees the record closed without asking the host again."""
    set_state = state_setter(harness)
    token = harness.token_for("code_alice", "alice")
    opened = submit_proof(harness, key, token)
    set_state(1, state="closed", merged=True, merge_commit_sha=MERGE_SHA, runs=[], reviews=[])

    snapshot(harness)  # the only read; it must reconcile

    record = harness.store.get_submission(opened["submission_id"])
    assert record is not None
    assert record.closed is not None, FINDING.format(
        "the snapshot filtered the row but left the store's record open"
    )
    assert [r.id for r in harness.store.list_open_submissions()] == []


def test_the_snapshot_reuses_the_cached_pull_state(harness: Harness, key: PrecheckKey) -> None:
    """Reconciliation rides the existing per-pull cache (C7): two snapshots inside the window
    are one host lookup per open submission, not one per read."""
    set_state = state_setter(harness)
    token = harness.token_for("code_alice", "alice")
    submit_proof(harness, key, token)
    set_state(1, state="open", merged=False, runs=[], reviews=[])

    snapshot(harness)
    after_first = lookups(harness)
    snapshot(harness)
    assert lookups(harness) == after_first, FINDING.format(
        "the snapshot asked the host again inside the freshness window"
    )


def test_a_host_failure_leaves_the_row_listed(harness: Harness, key: PrecheckKey) -> None:
    """C7: when the host cannot say, the submission stays on the list. An unreadable pull
    request is not a merged one, and the list must never quietly lose open work."""
    set_state = state_setter(harness)
    token = harness.token_for("code_alice", "alice")
    submit_proof(harness, key, token)
    set_state(1, state="open", merged=False, runs=[], reviews=[])
    snapshot(harness)

    age_pull_cache(harness)
    assert hasattr(harness.githost, "pr_lookup_failure"), "FakeGitHost.pr_lookup_failure"
    harness.githost.pr_lookup_failure = "GET /repos/.../pulls/1 returned 502"

    assert open_numbers(harness) == [1], FINDING.format(
        "a pull request the host could not describe was dropped from the open list"
    )


def test_list_submissions_tool_sees_the_reconciled_list(harness: Harness, key: PrecheckKey) -> None:
    """The MCP tool is the route body for body, so the fix reaches an agent's view too — the
    seat the finding was reported from."""
    set_state = state_setter(harness)
    token = harness.token_for("code_alice", "alice")
    submit_proof(harness, key, token)
    submit_annex(harness, token)
    set_state(1, state="closed", merged=True, merge_commit_sha=MERGE_SHA, runs=[], reviews=[])
    set_state(2, state="open", merged=False, runs=[], reviews=[])

    over_mcp = McpClient(harness).ok("list_submissions")
    assert [e["pr_number"] for e in over_mcp["open"]] == [2], FINDING.format(
        "list_submissions shows a merged pull request as open work"
    )
    assert over_mcp == snapshot(harness)
