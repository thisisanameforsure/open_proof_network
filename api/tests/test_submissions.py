"""F07-T3: ``POST /submissions`` (R1, R2, R14; AC1, AC2).

The service's only job here is to open a pull request that is indistinguishable from a
hand-opened one, and to refuse to open it unless a passing precheck by the same identity, over
the same bytes, already exists.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from api_fakes import (
    TUTORIAL_NODE,
    TUTORIAL_PROOF,
    Harness,
    PrecheckKey,
    make_precheck_key,
)

from opn_api import submissions
from opn_gate import bounce, schemas, submission

PREFIX = "targets/propositional/nodes/"
PROOF_PATH = f"{PREFIX}{TUTORIAL_NODE}/Proof.lean"
GRAPH_REPO = "thisisanameforsure/open_proof_network_graph"


@pytest.fixture
def key(tmp_path: Path) -> PrecheckKey:
    return make_precheck_key(tmp_path)


def bundle() -> dict[str, str]:
    return {PROOF_PATH: TUTORIAL_PROOF}


def submit(h: Harness, token: str, **overrides: Any) -> Any:
    body: dict[str, Any] = {
        "node_id": TUTORIAL_NODE,
        "artifact_type": "proof",
        "bundle": bundle(),
        "tooling": {"model": "claude-opus-5", "version": "2026-09", "harness": "claude-code"},
    }
    body.update(overrides)
    return h.client.post("/submissions", json=body, headers=h.auth(token))


def blocks(body: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """The two documents the pull-request body carries (R2)."""
    precheck_block = bounce.extract_block(body)
    assert precheck_block is not None
    parsed = submission.extract(body)
    assert parsed is not None
    return json.loads(precheck_block), parsed


def test_submission_opens_pr(harness: Harness, key: PrecheckKey) -> None:
    """AC1: a branch, a commit authored and signed off by the identity with the App as
    committer, and a pull request carrying both body blocks."""
    token = harness.token_for("code_alice", "alice")
    job = harness.tutorial_job(key, token=token)

    r = submit(harness, token, precheck_job_id=job["id"])
    assert r.status_code == 201, r.text
    doc = r.json()
    assert doc["pr_url"].startswith(f"https://github.com/{GRAPH_REPO}/pull/")
    assert doc["node_id"] == TUTORIAL_NODE
    assert doc["artifact_type"] == "proof"

    push = harness.githost.pushes[-1]
    assert push.repo == GRAPH_REPO
    assert push.branch == "submit/" + doc["submission_id"]
    assert push.base == harness.settings.graph_branch
    assert push.files == bundle()
    # The author is the ledger identity at a reserved-TLD address (Q6); the committer is the
    # App, named rather than omitted, because GitHub copies the author into an absent committer
    # and the D-23 split would collapse (found on the live host, F07-T6).
    assert push.author is not None
    assert push.author.name == "alice"
    assert push.author.email == "alice@anon.opn.invalid"
    assert push.committer is not None
    assert push.committer.name == harness.settings.committer_name
    assert push.committer.email == harness.settings.committer_email
    assert push.committer.name != push.author.name
    assert push.message.endswith("Signed-off-by: alice <alice@anon.opn.invalid>\n")

    pr = harness.githost.pulls[-1]
    assert pr.repo == GRAPH_REPO
    assert pr.head == push.branch
    assert pr.base == harness.settings.graph_branch
    assert pr.title == f"proof: {TUTORIAL_NODE}"
    attestation, meta = blocks(pr.body)
    assert attestation["node_id"] == TUTORIAL_NODE
    assert attestation["signature"]["kind"] == "service"
    assert meta["identity"] == {"pseudonym": "alice", "proof_kind": "github"}
    assert meta["artifact_type"] == "proof"
    assert meta["precheck_job_id"] == job["id"]
    assert meta["tooling"]["model"] == "claude-opus-5"
    assert schemas.violations(meta, submission.SCHEMA) == []
    assert submission.model_and_tooling(meta) == "claude-opus-5 2026-09 claude-code"


def test_precheck_binding(harness: Harness, key: PrecheckKey) -> None:
    """AC2: another identity's precheck, a failing one, and a different bundle are each a 400
    naming the mismatch, and nothing is pushed."""
    alice = harness.token_for("code_alice", "alice")
    bob = harness.token_for("code_bob", "bob")
    mine = harness.tutorial_job(key, token=alice)
    theirs = harness.tutorial_job(key, token=bob)
    failing = harness.tutorial_job(key, token=alice, verdict="fail")
    before = len(harness.githost.pushes)

    cases = {
        "precheck-not-yours": {"precheck_job_id": theirs["id"]},
        "precheck-not-passing": {"precheck_job_id": failing["id"]},
        "precheck-unknown": {"precheck_job_id": "01M00000000000000000000000"},
        "precheck-required": {},
        "precheck-bundle-differs": {
            "precheck_job_id": mine["id"],
            "bundle": {PROOF_PATH: TUTORIAL_PROOF + "-- edited\n"},
        },
    }
    for code, overrides in cases.items():
        r = submit(harness, alice, **overrides)
        assert r.status_code == 400, (code, r.text)
        assert r.json()["error"] == code, r.text
    assert len(harness.githost.pushes) == before
    assert harness.githost.pulls == []

    # The same submission, correctly bound, does open — so the refusals above are about the
    # binding and not about something else being wrong with the request.
    assert submit(harness, alice, precheck_job_id=mine["id"]).status_code == 201


def test_anonymous_precheck_cannot_be_submitted(harness: Harness, key: PrecheckKey) -> None:
    """R1: an anonymous tutorial job belongs to no identity, so no identity may submit on it."""
    token = harness.token_for("code_alice", "alice")
    anonymous = harness.tutorial_job(key)  # no token: the D-19 account-free path
    r = submit(harness, token, precheck_job_id=anonymous["id"])
    assert r.status_code == 400
    assert r.json()["error"] == "precheck-not-yours"


def test_submission_needs_a_token(harness: Harness) -> None:
    r = harness.client.post("/submissions", json={"node_id": TUTORIAL_NODE})
    assert r.status_code == 401
    assert harness.githost.pushes == []


def test_request_validation(harness: Harness, key: PrecheckKey) -> None:
    """R2, R14: the artifact type is D-12's five, and declared tooling is capped, not trusted."""
    token = harness.token_for("code_alice", "alice")
    job = harness.tutorial_job(key, token=token)
    ok = {"precheck_job_id": job["id"]}

    assert submit(harness, token, artifact_type="sketch", **ok).status_code == 400
    assert submit(harness, token, artifact_type=None, **ok).status_code == 400
    long = "x" * (submissions.MAX_TOOLING_CHARS + 1)
    r = submit(harness, token, tooling={"model": long}, **ok)
    assert r.status_code == 400
    assert r.json()["error"] == "tooling-invalid"
    r = submit(harness, token, node_id="no-such-node", **ok)
    assert r.status_code == 404
    r = submit(harness, token, bundle={f"{PREFIX}{TUTORIAL_NODE}/Statement.lean": "x"}, **ok)
    assert r.status_code == 400
    assert r.json()["error"] == "path-forbidden"

    # Undeclared tooling is allowed: the gate is blind to it (D-1), and R13 records it as such.
    r = submit(harness, token, tooling=None, **ok)
    assert r.status_code == 201
    _, meta = blocks(harness.githost.pulls[-1].body)
    assert meta["tooling"] == {"model": None, "version": None, "harness": None}
    assert submission.model_and_tooling(meta) == submission.UNDECLARED


def test_host_failure_is_never_a_silent_success(harness: Harness, key: PrecheckKey) -> None:
    """C7: if the pull request cannot be opened, the caller is told — nothing is reported as
    submitted that is not."""
    token = harness.token_for("code_alice", "alice")
    job = harness.tutorial_job(key, token=token)
    harness.githost.pr_failure = "POST /repos/.../pulls returned 403"
    r = submit(harness, token, precheck_job_id=job["id"])
    assert r.status_code == 502
    assert r.json()["error"] == "pull-request-failed"
