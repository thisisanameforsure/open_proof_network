"""Finding 8 (2026-09-13, the live MCP contribution; the 2026-09-12 register's #13): the
attestation's id is zero-padded on disk and the tool takes the padding literally.

The guide says ``attestations/<pull request number>.json``; the post-merge job writes
``attestations/000033.json``. ``get_submission`` builds the path from the argument as given, so
``"33"`` — the number a contributor reads off the pull request — is ``not-found`` while
``"000033"`` answers. Asserted here (plan Phase 0, F09-T6): both spellings resolve to the same
record. The padded spelling passes today and is not marked; the unpadded one is held as a strict
xfail until F09-T6 lands (conventions §2).

The plan's second half — a merged non-building mode (an append) answering
``no-attestation-for-mode`` rather than ``not-found`` — was declined here on 2026-09-13: nothing
the fake host served tied a pull-request number to the mode that merged under it. The seam now
has a name (2026-09-14, plan F07-T16): the service records every pull request it opens, with
its kind, and reads the pull request's live state from the host. That half is asserted in
``test_finding_pending_submissions.py`` (``test_a_merged_annex_answers_no_attestation_for_mode``),
and the pending half — ``get_submission`` on an open pull request answering its live state
rather than ``not-found`` — is now asserted here, 2026-09-14, held as a strict xfail until F09-T7
lands.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import samples
from api_fakes import PROOF_PREFIX, TUTORIAL_NODE, TUTORIAL_PROOF, Harness, make_precheck_key
from mcp_client import McpClient, plain

PADDED = "000033"
ATTESTATION_PATH = f"attestations/{PADDED}.json"
FINDING_8 = (
    "finding 8 (F09-R5, D-28): get_submission reads attestations/<id>.json with the id as given, "
    "so the unpadded pull-request number the guide names is not-found; "
    "fix: F09-T6 (Mike, 2026-09-13)"
)


def seed_attestation(harness: Harness) -> None:
    harness.githost.files[ATTESTATION_PATH] = json.dumps(
        samples.attestation(node_id=TUTORIAL_NODE, graph_commit="5" * 40)
    ).encode()
    harness.context.files.clear()


@pytest.mark.parametrize("submission_id", [PADDED, "33", "0000000033"])
def test_get_submission_resolves_the_padded_and_unpadded_id(
    harness: Harness, submission_id: str
) -> None:
    """The pull-request number and the file's zero-padded name are the same attestation.

    Rewritten by F09-T7 (2026-09-14): the tool is ``GET /submissions/{id}`` now, so the
    attestation is the answer's ``attestation`` field rather than the whole result, and the
    unpadded spelling (FINDING_8, held for F09-T6) passes with it. A pull request opened by hand
    has no record, so ``submission`` is null. Leading zeros beyond six are the same number."""
    seed_attestation(harness)
    doc = McpClient(harness).ok("get_submission", {"submission_id": submission_id})
    assert doc["submission"] is None
    assert doc["attestation_path"] == ATTESTATION_PATH
    assert doc["attestation"] == plain(harness, ATTESTATION_PATH)
    assert doc["attestation"]["node_id"] == TUTORIAL_NODE
    assert doc["attestation_note"] is None


@pytest.mark.xfail(
    strict=True,
    reason=(
        "finding pending-submissions (F09-R5, D-28): get_submission is GET /submissions/{id}, "
        "which does not know a POST /submissions pull request that was never recorded; "
        "fix: F09-T7 (Mike, 2026-09-14); needs the submissions.py record call; after the other "
        "session's commit"
    ),
)
def test_get_submission_answers_pending_state_for_an_open_pull_request(
    harness: Harness, tmp_path: Path
) -> None:
    """The number ``POST /submissions`` answered is watchable before anything merges: the tool
    answers the pull request's live state (open, its failed gate run) with no attestation and
    ``attestation_note: not-merged``, whichever spelling of the number is given."""
    set_state = getattr(harness.githost, "set_pull_request_state", None)
    assert callable(set_state), "FakeGitHost.set_pull_request_state does not exist (F07-T16)"
    key = make_precheck_key(tmp_path)
    token = harness.token_for("code_alice", "alice")
    job = harness.tutorial_job(key, token=token)
    opened = harness.client.post(
        "/submissions",
        json={
            "node_id": TUTORIAL_NODE,
            "artifact_type": "proof",
            "bundle": {f"{PROOF_PREFIX}{TUTORIAL_NODE}/Proof.lean": TUTORIAL_PROOF},
            "precheck_job_id": job["id"],
        },
        headers=harness.auth(token),
    )
    assert opened.status_code == 201, opened.text  # guard: the submission opens today
    number = opened.json()["pr_number"]
    set_state(
        number,
        state="open",
        merged=False,
        mergeable_state="blocked",
        runs=[{"name": "gate", "status": "completed", "conclusion": "failure", "url": "u"}],
        reviews=[],
    )

    client = McpClient(harness)
    doc = client.ok("get_submission", {"submission_id": str(number)})
    assert doc["submission"]["id"] == opened.json()["submission_id"]
    assert doc["pull_request"]["state"] == "open"
    assert doc["pull_request"]["runs"][0]["conclusion"] == "failure"
    assert doc["attestation"] is None
    assert doc["attestation_note"] == "not-merged"
    assert client.ok("get_submission", {"submission_id": f"{number:06d}"}) == doc
