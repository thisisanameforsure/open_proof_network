"""F25-T3 / AC3: the service requires the ``automation`` block of every artifact submission and
refuses without it before anything opens (F25-R2; D-23 v3.37, F25-Q7).

``POST /submissions`` refuses ``automation-missing`` (naming the field) and ``automation-invalid``
with no branch pushed and no pull request opened — the F13-T21 rule. An accepted block is written
into the pull request body's ``opn-submission`` block (``submission-meta/v2``), served on the
submission's row, and, when offered to ``POST /precheck``, validated and echoed on the job; it is
not required there (F25-Q14: the tutorial token flow prechecks with no identity). The MCP tools
refuse in their own envelope.
"""

from __future__ import annotations

import json
from pathlib import Path
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
from test_submissions import blocks, submit

from opn_api import submissions
from opn_api.store import Submission
from opn_gate import schemas, submission

PROOF_PATH = f"{PROOF_PREFIX}{TUTORIAL_NODE}/Proof.lean"


def automation(**overrides: Any) -> dict[str, Any]:
    doc: dict[str, Any] = {
        "method": "agent",
        "models": ["claude-fable-5-1"],
        "framework": "Claude Code 2.1",
    }
    doc.update(overrides)
    return doc


@pytest.fixture
def key(tmp_path: Path) -> PrecheckKey:
    return make_precheck_key(tmp_path)


def submit_without(h: Harness, token: str, **overrides: Any) -> Any:
    """``test_submissions.submit``'s body with the block left out altogether (not null)."""
    body: dict[str, Any] = {
        "node_id": TUTORIAL_NODE,
        "artifact_type": "proof",
        "bundle": {PROOF_PATH: TUTORIAL_PROOF},
        "tooling": {"model": "claude-opus-5", "version": "2026-09", "harness": "claude-code"},
    }
    body.update(overrides)
    return h.client.post("/submissions", json=body, headers=h.auth(token))


def opened(h: Harness) -> tuple[int, int]:
    """What the fake host has been asked to create: branches pushed and pull requests opened."""
    return len(h.githost.pushes), len(h.githost.pulls)


# --- POST /submissions: refused before anything opens --------------------------------------------


def test_a_submission_without_the_block_is_refused_and_nothing_opens(
    harness: Harness, key: PrecheckKey
) -> None:
    token = harness.token_for("code_alice", "alice")
    job = harness.tutorial_job(key, token=token)
    before = opened(harness)
    for r in (
        submit_without(harness, token, precheck_job_id=job["id"]),
        submit(harness, token, precheck_job_id=job["id"], automation=None),
    ):
        assert r.status_code == 400, r.text
        assert r.json()["error"] == "automation-missing"
        assert "automation" in r.json()["message"]
    assert opened(harness) == before, "a refused submission pushed or opened something"
    # the job is not spent: the same precheck still backs a submission that carries the block
    ok = submit(harness, token, precheck_job_id=job["id"], automation=automation())
    assert ok.status_code == 201, ok.text


@pytest.mark.parametrize("field", ["method", "models", "framework"])
def test_a_block_missing_a_required_field_is_refused_by_name(
    harness: Harness, key: PrecheckKey, field: str
) -> None:
    token = harness.token_for("code_alice", "alice")
    job = harness.tutorial_job(key, token=token)
    before = opened(harness)
    block = automation()
    del block[field]
    r = submit(harness, token, precheck_job_id=job["id"], automation=block)
    assert r.status_code == 400, r.text
    assert r.json()["error"] == "automation-missing"
    assert field in r.json()["message"], r.json()["message"]
    assert opened(harness) == before


@pytest.mark.parametrize(
    "block",
    [
        "agent",
        {"method": "llm", "models": ["m"], "framework": "f"},
        {"method": "agent", "models": [], "framework": "f"},
        {"method": "agent", "models": "m", "framework": "f"},
        {"method": "agent", "models": ["m"], "framework": "f", "tokens": {"input": "12"}},
        {
            "method": "agent",
            "models": ["m"],
            "framework": "f",
            "tokens": {"input": 1, "output": 2.5},
        },
        {"method": "agent", "models": ["m"], "framework": "f", "cost_usd": 12.4},
    ],
)
def test_a_malformed_block_is_refused_and_nothing_opens(
    harness: Harness, key: PrecheckKey, block: Any
) -> None:
    token = harness.token_for("code_alice", "alice")
    job = harness.tutorial_job(key, token=token)
    before = opened(harness)
    r = submit(harness, token, precheck_job_id=job["id"], automation=block)
    assert r.status_code == 400, r.text
    assert r.json()["error"] == "automation-invalid", r.text
    assert opened(harness) == before


def test_every_artifact_type_on_the_route_requires_it(harness: Harness, key: PrecheckKey) -> None:
    """The route's rule is by route, not by type: the refusal comes before any type-specific check
    reads the bundle, so each of D-12's five is refused the same way (R2)."""
    token = harness.token_for("code_alice", "alice")
    assert set(submissions.ARTIFACT_TYPES) == {
        "proof",
        "counterexample",
        "vacuity",
        "reduction",
        "partial",
    }
    for artifact_type in submissions.ARTIFACT_TYPES:
        before = opened(harness)
        r = submit_without(harness, token, artifact_type=artifact_type, precheck_job_id="0" * 26)
        assert r.status_code == 400, (artifact_type, r.text)
        assert r.json()["error"] == "automation-missing", (artifact_type, r.text)
        assert opened(harness) == before


# --- an accepted block: the pull request body, the rows, the precheck result ---------------------


def test_an_accepted_block_is_written_into_the_opn_submission_block(
    harness: Harness, key: PrecheckKey
) -> None:
    token = harness.token_for("code_alice", "alice")
    job = harness.tutorial_job(key, token=token)
    block = automation(
        tool_setup="the MCP server and the guide",
        wall_time="about 40 minutes",
        tokens={"input": 120000, "output": 9000},
        hardware="one laptop; hosted models",
        spend="subscription",
    )
    r = submit(harness, token, precheck_job_id=job["id"], automation=block)
    assert r.status_code == 201, r.text
    _attestation, meta = blocks(harness.githost.pulls[-1].body)
    assert meta["schema"] == "submission-meta/v2" == submission.SCHEMA
    assert meta["automation"] == block
    assert schemas.violations(meta, submission.SCHEMA) == []
    assert submission.automation(meta) == block
    # the free string is unchanged beside it (R3)
    assert submission.model_and_tooling(meta) == "claude-opus-5 2026-09 claude-code"


def test_the_submission_rows_carry_the_block(harness: Harness, key: PrecheckKey) -> None:
    token = harness.token_for("code_alice", "alice")
    job = harness.tutorial_job(key, token=token)
    r = submit(harness, token, precheck_job_id=job["id"], automation=automation())
    assert r.status_code == 201, r.text
    sid = r.json()["submission_id"]
    one = harness.client.get(f"/submissions/{sid}")
    assert one.status_code == 200, one.text
    assert one.json()["submission"]["automation"] == automation()
    listed = harness.client.get("/submissions.json")
    assert listed.status_code == 200, listed.text
    (row,) = [e for e in listed.json()["open"] if e["id"] == sid]
    assert row["automation"] == automation()
    mine = harness.client.get("/submissions/mine", headers=harness.auth(token))
    assert mine.status_code == 200, mine.text
    assert [e["automation"] for e in mine.json()["open"]] == [automation()]


def test_an_older_row_without_the_block_is_served_with_null(harness: Harness) -> None:
    """A record stored before the field existed: the store's reader fills it with null, as the
    ledger lift does (R3), and every listing serves it."""
    harness.store.put_submission(
        Submission(
            id="01J000000000000000000000AA",
            kind="proof",
            node_id=TUTORIAL_NODE,
            target_id="propositional",
            pr_number=7,
            pr_url="https://github.com/x/y/pull/7",
            pseudonym="alice",
            precheck_job_id=None,
            created="2026-09-01T00:00:00Z",
        )
    )
    one = harness.client.get("/submissions/01J000000000000000000000AA")
    assert one.status_code == 200, one.text
    assert one.json()["submission"]["automation"] is None


def precheck(h: Harness, token: str | None, **extra: Any) -> Any:
    body: dict[str, Any] = {"node_id": TUTORIAL_NODE, "bundle": {PROOF_PATH: TUTORIAL_PROOF}}
    body.update(extra)
    return h.client.post("/precheck", json=body, headers=h.auth(token) if token else {})


def test_precheck_does_not_require_the_block(harness: Harness, key: PrecheckKey) -> None:
    """F25-Q14: required at submission, validated when offered at precheck. The anonymous
    tutorial precheck is how an identity is minted, and it has nothing to declare yet."""
    harness.commit_precheck_key(key.public)
    anonymous = precheck(harness, None)
    assert anonymous.status_code == 202, anonymous.text
    assert anonymous.json()["automation"] is None
    token = harness.token_for("code_alice", "alice")
    owned = precheck(harness, token)
    assert owned.status_code == 202, owned.text
    assert owned.json()["automation"] is None


def test_precheck_validates_the_block_when_offered_and_nothing_is_dispatched(
    harness: Harness, key: PrecheckKey
) -> None:
    harness.commit_precheck_key(key.public)
    token = harness.token_for("code_alice", "alice")
    before = opened(harness)
    dispatched = len(harness.githost.dispatches)
    malformed = precheck(
        harness, token, automation={"method": "llm", "models": [], "framework": "f"}
    )
    assert malformed.status_code == 400, malformed.text
    assert malformed.json()["error"] == "automation-invalid"
    assert "method" in malformed.json()["message"] and "models" in malformed.json()["message"]
    # an offered block is held to the same rule as a submitted one: an incomplete block names
    # the field it lacks, the same code the submission would give (one checker, two routes)
    incomplete = precheck(harness, token, automation={"method": "agent"})
    assert incomplete.status_code == 400, incomplete.text
    assert incomplete.json()["error"] == "automation-missing"
    message = incomplete.json()["message"]
    assert "models" in message and "framework" in message
    assert opened(harness) == before
    assert len(harness.githost.dispatches) == dispatched


def test_precheck_echoes_the_block_on_the_job_and_in_its_result(
    harness: Harness, key: PrecheckKey
) -> None:
    harness.commit_precheck_key(key.public)
    token = harness.token_for("code_alice", "alice")
    block = automation(wall_time="an hour")
    created = precheck(harness, token, automation=block)
    assert created.status_code == 202, created.text
    assert created.json()["automation"] == block
    job_id = created.json()["id"]
    # the branch the job runs from carries it in job.json, for the runner and for a reader
    push = harness.githost.pushes[-1]
    assert push.branch == f"job/{job_id}"
    assert json.loads(push.files["job.json"])["automation"] == block
    polled = harness.client.get(f"/precheck/{job_id}")
    assert polled.status_code == 200, polled.text
    assert polled.json()["automation"] == block


# --- the MCP tools: the refusal has the tool's shape ---------------------------------------------


def test_mcp_submit_proof_requires_the_block_in_its_own_envelope(
    harness: Harness, key: PrecheckKey
) -> None:
    client = McpClient(harness)
    token = harness.token_for("code_alice", "alice")
    job = harness.tutorial_job(key, token=token)
    base = {
        "node_id": TUTORIAL_NODE,
        "artifact_type": "proof",
        "bundle": {PROOF_PATH: TUTORIAL_PROOF},
        "precheck_job_id": job["id"],
    }
    before = opened(harness)
    # the tool's schema requires it, so the adapter names the gap before the endpoint is reached
    missing = client.failed("submit_proof", base, token=token)
    assert missing["error"] == "arguments-invalid"
    assert "automation" in missing["message"]
    assert missing["source"] == "adapter"
    # a malformed block the schema admits by shape reaches the route and is refused by its code
    bad = client.failed("submit_proof", {**base, "automation": {"method": "agent"}}, token=token)
    assert bad["error"] in ("automation-invalid", "automation-missing", "arguments-invalid"), bad
    assert opened(harness) == before
    # and the good one opens
    good = client.ok("submit_proof", {**base, "automation": automation()}, token=token)
    assert good["status"] == 201, good
    _att, meta = blocks(harness.githost.pulls[-1].body)
    assert meta["automation"] == automation()


def test_mcp_precheck_submission_takes_the_block_optionally(
    harness: Harness, key: PrecheckKey
) -> None:
    harness.commit_precheck_key(key.public)
    client = McpClient(harness)
    token = harness.token_for("code_alice", "alice")
    args = {"node_id": TUTORIAL_NODE, "bundle": {PROOF_PATH: TUTORIAL_PROOF}}
    without = client.ok("precheck_submission", args, token=token)
    assert without["status"] == 202, without
    assert without["body"]["automation"] is None
    bad = client.failed(
        "precheck_submission", {**args, "automation": {"method": "agent"}}, token=token
    )
    assert bad["error"] in ("automation-invalid", "arguments-invalid"), bad
    assert bad["source"] in ("api", "adapter")
    with_block = client.ok("precheck_submission", {**args, "automation": automation()}, token=token)
    assert with_block["status"] == 202, with_block
    assert with_block["body"]["automation"] == automation()
