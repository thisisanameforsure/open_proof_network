"""Finding precheck-pending-proposal (testers 2026-09-27, five of six): a proof of a node that
exists only in an open proposal could not be prechecked until the proposal merged. ``POST
/precheck`` answered ``409 node-pending``, so a variant and its proof cost two full trips through
the merge queue, one after the other, where the proof's check could have run beside the first.

F06-T10 (the owner's ruling on what F08-Q23 left open): when the proposal's pull request has a
green gate (``waiting_on`` ``merge`` or ``branch-update``), the precheck runs against the
proposal's head commit. The job names the pull request and the commit, and the contributor
submits once the proposal has merged, reusing the passed precheck. A proposal whose gate is not
green is still ``409 node-pending``, and now says the precheck opens once the gate is green.

The tricky part is the last step: the precheck attestation was made at the proposal's head, and
the proof's gate run checks it against the merged tree (``bounce.evaluate``: node, statement
hash, verdict, signature, age — not the graph commit). That holds because nothing at merge or
after it rewrites a proposed node's ``Statement.lean``: the own-Context import (F08-T13) is
written by the service when the proposal opens, and the post-merge job writes only new holes'
statements, ``Context.lean`` and ``META.yaml`` deps. The test below drives the whole path.
"""

from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest
import samples
import yaml
from api_fakes import Harness, PrecheckKey, make_precheck_key, result_zip
from test_precheck import PROOF
from test_proposals import (
    DEP_STATEMENT,
    GRAPH_PATH,
    NODES,
    STATEMENT,
    TARGET,
    WITNESS,
    materialise,
)

from opn_gate import bounce, layout, schemas

HEAD = "a" * 40
MERGE = "b" * 40
GREEN = {"name": "gate", "status": "completed", "conclusion": "success"}


@pytest.fixture
def token(harness: Harness) -> str:
    return harness.token_for("code_alice", "alice")


@pytest.fixture
def key(tmp_path: Path) -> PrecheckKey:
    return make_precheck_key(tmp_path)


def propose(harness: Harness, token: str) -> tuple[str, int, dict[str, str]]:
    """Open a variant through the service, and let its branch's head carry what was pushed."""
    r = harness.client.post(
        "/proposals/variant",
        json={"target_id": TARGET, "statement": STATEMENT, "witness": WITNESS},
        headers=harness.auth(token),
    )
    assert r.status_code == 201, r.text
    files = dict(harness.githost.pushes[-1].files)
    harness.githost.files_at[HEAD] = {p: c.encode() for p, c in files.items()}
    return str(r.json()["node_id"]), int(r.json()["pr_number"]), files


def gate(harness: Harness, number: int, **state: Any) -> None:
    harness.githost.set_pull_request_state(number, head_sha=HEAD, **state)
    harness.context.pulls.pop(number, None)


def precheck(harness: Harness, token: str, node_id: str) -> Any:
    return harness.client.post(
        "/precheck",
        json={"node_id": node_id, "bundle": {f"{NODES}{node_id}/Proof.lean": PROOF}},
        headers=harness.auth(token),
    )


def gate_hash(files: dict[str, str], node_id: str, root: Path) -> str:
    """The statement hash the gate and the products take of the tree (``layout.load_node``)."""
    materialise(files, root)
    node = layout.load_node(root / NODES / node_id, TARGET)
    assert isinstance(node, layout.Node), node
    return node.statement.statement_hash


@pytest.mark.parametrize(
    ("mergeable_state", "waiting_on"), [("clean", "merge"), ("behind", "branch-update")]
)
def test_a_green_proposal_can_be_prechecked_at_its_head(
    harness: Harness, token: str, tmp_path: Path, mergeable_state: str, waiting_on: str
) -> None:
    node_id, number, files = propose(harness, token)
    gate(harness, number, mergeable_state=mergeable_state, runs=[GREEN])
    pushes = len(harness.githost.pushes)

    r = precheck(harness, token, node_id)
    assert r.status_code == 202, r.text
    job = r.json()
    assert job["target_id"] == TARGET
    assert job["graph_commit"] == HEAD  # the workflow checks the graph out at the proposal head
    assert job["proposal"]["pr_number"] == number
    assert job["proposal"]["head_sha"] == HEAD
    assert f"#{number}" in job["proposal"]["message"] and "merge" in job["proposal"]["message"]

    push = harness.githost.pushes[pushes]
    record = json.loads(push.files["job.json"])
    assert record["graph_commit"] == HEAD
    assert record["statement_hash"] == gate_hash(files, node_id, tmp_path / "g")
    assert record["proposal"] == {
        "pr_number": number,
        "pr_url": job["proposal"]["pr_url"],
        "head_sha": HEAD,
    }
    # the answer on read says the same, so a poller knows to submit after the merge
    again = harness.client.get(f"/precheck/{job['id']}").json()
    assert again["proposal"] == job["proposal"]


@pytest.mark.parametrize(
    ("state", "waiting_on"),
    [
        ({"runs": [{"name": "gate", "status": "in_progress", "conclusion": None}]}, "gate"),
        (
            {"runs": [{"name": "gate", "status": "completed", "conclusion": "failure"}]},
            "gate-failed",
        ),
        ({"mergeable_state": "dirty", "runs": [GREEN]}, "conflict"),
        (
            {
                "runs": [
                    {
                        "name": "gate",
                        "status": "completed",
                        "conclusion": "failure",
                        "jobs": [
                            {
                                "name": "gate (sandbox)",
                                "status": "completed",
                                "conclusion": "success",
                            },
                            {
                                "name": "step 9 (review)",
                                "status": "completed",
                                "conclusion": "failure",
                            },
                        ],
                    }
                ]
            },
            "step9-review",
        ),
    ],
)
def test_a_proposal_whose_gate_is_not_green_is_still_pending(
    harness: Harness, token: str, state: dict[str, Any], waiting_on: str
) -> None:
    node_id, number, _ = propose(harness, token)
    gate(harness, number, **state)
    pushes = len(harness.githost.pushes)

    r = precheck(harness, token, node_id)
    assert r.status_code == 409, r.text
    doc = r.json()
    assert doc["error"] == "node-pending"
    assert doc["details"]["waiting_on"] == waiting_on
    assert "once" in doc["message"] and "gate is green" in doc["message"]
    assert len(harness.githost.pushes) == pushes and not harness.githost.dispatches


def test_a_green_proposal_whose_head_cannot_be_read_stays_pending(
    harness: Harness, token: str
) -> None:
    """C7: a job is never pinned to a tree the service could not read. The head's statement is
    missing (the branch moved, or the host answered 404) and the answer is ``node-pending``, as
    before; nothing is pushed or dispatched."""
    node_id, number, _ = propose(harness, token)
    harness.githost.files_at.pop(HEAD)
    gate(harness, number, mergeable_state="clean", runs=[GREEN])
    pushes = len(harness.githost.pushes)
    r = precheck(harness, token, node_id)
    assert r.status_code == 409, r.text
    assert r.json()["error"] == "node-pending"
    assert len(harness.githost.pushes) == pushes and not harness.githost.dispatches


def test_a_submission_before_the_merge_says_the_precheck_is_open(
    harness: Harness, token: str
) -> None:
    node_id, number, _ = propose(harness, token)
    gate(harness, number, mergeable_state="clean", runs=[GREEN])
    r = harness.client.post(
        "/submissions",
        json={
            "node_id": node_id,
            "artifact_type": "proof",
            "bundle": {f"{NODES}{node_id}/Proof.lean": PROOF},
            "tooling": {"model": None, "harness": None},
        },
        headers=harness.auth(token),
    )
    assert r.status_code == 409, r.text
    assert r.json()["error"] == "node-pending"
    assert "precheck" in r.json()["message"] and "already" in r.json()["message"]


def merge(harness: Harness, number: int, node_id: str, files: dict[str, str], root: Path) -> str:
    """The proposal merges: its files reach ``main`` as they were at the head (nothing at the merge
    or after it rewrites them), and the post-merge job renders the node into the products with the
    hash the gate takes of the merged tree."""
    harness.githost.set_pull_request_state(
        number, state="closed", merged=True, head_sha=HEAD, merge_commit_sha=MERGE
    )
    harness.context.pulls.pop(number, None)
    for path, content in files.items():
        harness.githost.files[path] = content.encode()
    merged_hash = gate_hash(files, node_id, root)
    doc = json.loads(harness.githost.files[GRAPH_PATH])
    doc["nodes"].append(
        {
            "node_id": node_id,
            "status": "ready",
            "cause": None,
            "deps": [],
            "origin": "authored",
            "statement_hash": merged_hash,
            "relation": None,
            "tutorial": False,
            "trust_base": None,
            "proof_commit": None,
        }
    )
    harness.githost.files[GRAPH_PATH] = json.dumps(doc).encode()
    harness.context.files.clear()
    return merged_hash


def test_a_precheck_at_the_head_binds_a_submission_after_the_merge(
    harness: Harness, token: str, key: PrecheckKey, tmp_path: Path
) -> None:
    """The whole path: precheck at the proposal head, the run passes, the proposal merges, the
    proof is submitted with that job, and the attestation in the pull request's body passes the
    gate's bounce rule against the merged tree's ``Statement.lean``."""
    harness.commit_precheck_key(key.public)
    node_id, number, files = propose(harness, token)
    gate(harness, number, mergeable_state="clean", runs=[GREEN])
    job = precheck(harness, token, node_id).json()
    assert job["graph_commit"] == HEAD
    record = json.loads(harness.githost.pushes[-1].files["job.json"])
    artifact = result_zip(
        job_id=job["id"],
        node_id=node_id,
        graph_commit=HEAD,
        bundle_digest=job["bundle_digest"],
        key=key,
        statement_hash=record["statement_hash"],  # what the run takes of the tree at the head
    )
    harness.githost.finish_run(f"job/{job['id']}", artifact=(f"result-{job['id']}", artifact))
    assert harness.client.get(f"/precheck/{job['id']}").json()["state"] == "done"

    merged_hash = merge(harness, number, node_id, files, tmp_path / "merged")
    r = harness.client.post(
        "/submissions",
        json={
            "node_id": node_id,
            "artifact_type": "proof",
            "bundle": {f"{NODES}{node_id}/Proof.lean": PROOF},
            "tooling": {"model": None, "harness": None},
            "precheck_job_id": job["id"],
        },
        headers=harness.auth(token),
    )
    assert r.status_code == 201, r.text

    body = harness.githost.pulls[-1].body
    attached = json.loads(bounce.extract_block(body) or "{}")
    statement = (tmp_path / "merged" / NODES / node_id / "Statement.lean").read_bytes()
    assert schemas.content_hash(statement) == merged_hash  # the bounce rule's hash, cli.run_gate
    decision = bounce.evaluate(
        bounce.PrecheckPolicy(
            pr_body=body,
            accepted_signatures=("service",),
            max_age_s=86400,
            now=bounce.parse_timestamp(attached["signature"]["timestamp"]) + timedelta(hours=1),
            node_id=node_id,
            statement_hash=schemas.content_hash(statement),
        )
    )
    assert not decision.bounced, decision.reason


def test_a_statement_changed_after_the_precheck_is_refused_at_submission(
    harness: Harness, token: str, key: PrecheckKey, tmp_path: Path
) -> None:
    """The one way the head's precheck could miss the merged tree: the proposal's branch moved
    to a different statement after the job ran. The gate would bounce the attestation; the
    service says so before a pull request is opened."""
    harness.commit_precheck_key(key.public)
    node_id, number, files = propose(harness, token)
    gate(harness, number, mergeable_state="clean", runs=[GREEN])
    job = precheck(harness, token, node_id).json()
    record = json.loads(harness.githost.pushes[-1].files["job.json"])
    artifact = result_zip(
        job_id=job["id"],
        node_id=node_id,
        graph_commit=HEAD,
        bundle_digest=job["bundle_digest"],
        key=key,
        statement_hash=record["statement_hash"],
    )
    harness.githost.finish_run(f"job/{job['id']}", artifact=(f"result-{job['id']}", artifact))

    statement_path = f"{NODES}{node_id}/Statement.lean"
    moved = files[statement_path].replace("p ∨ q", "q ∨ p")  # noqa: RUF001
    assert moved != files[statement_path]
    meta_path = f"{NODES}{node_id}/META.yaml"
    meta = yaml.safe_load(files[meta_path])
    meta["statement-hash"] = schemas.content_hash(moved.encode())
    changed = {**files, statement_path: moved, meta_path: yaml.safe_dump(meta, sort_keys=False)}
    merge(harness, number, node_id, changed, tmp_path / "merged")
    pulls = len(harness.githost.pulls)
    r = harness.client.post(
        "/submissions",
        json={
            "node_id": node_id,
            "artifact_type": "proof",
            "bundle": {f"{NODES}{node_id}/Proof.lean": PROOF},
            "tooling": {"model": None, "harness": None},
            "precheck_job_id": job["id"],
        },
        headers=harness.auth(token),
    )
    assert r.status_code == 400, r.text
    assert r.json()["error"] == "precheck-statement-differs"
    assert len(harness.githost.pulls) == pulls


def test_verify_mode_reads_a_green_proposal_at_its_head(harness: Harness, token: str) -> None:
    """``POST /check`` in verify mode compares a proof with the node's statement; for a green
    proposal that statement, and the Context it imports, are read at the head commit."""
    node_id, number, files = propose(harness, token)
    gate(harness, number, mergeable_state="clean", runs=[GREEN])
    harness.githost.files[f"targets/{TARGET}/gate-spec.json"] = schemas.canonical_json(
        samples.gate_spec(mathlib_sha="0df444a360eaa60ab8c11dca51a86af692955474")
    )
    harness.context.files.clear()
    r = harness.client.post(
        "/check",
        json={
            "target_id": TARGET,
            "node_id": node_id,
            "mode": "verify",
            "content": files[f"{NODES}{node_id}/Statement.lean"].replace("sorry", "trivial"),
        },
        headers=harness.auth(token),
    )
    assert r.status_code == 200, r.text
    call = harness.axle.calls[-1]
    assert call.method == "verify_proof"
    assert "OpnProp.and_weaken" in (call.formal_statement or "")


def test_a_green_proposal_on_an_unproved_dependency_is_refused_as_blocked(
    harness: Harness, token: str
) -> None:
    """A proposal whose ``META.yaml`` declares a dependency that is not proved would merge
    ``blocked``; its precheck can only fail at the dependency check, so it is refused as a blocked
    node on main is (F06-T6), before any job exists."""
    harness.githost.files[f"{NODES}and-reassoc/Statement.lean"] = DEP_STATEMENT.encode()
    r = harness.client.post(
        "/proposals/speculative",
        json={
            "target_id": TARGET,
            "statement": STATEMENT,
            "witness": WITNESS,
            "deps": ["and-reassoc"],
        },
        headers=harness.auth(token),
    )
    assert r.status_code == 201, r.text
    node_id, number = str(r.json()["node_id"]), int(r.json()["pr_number"])
    pushed = harness.githost.pushes[-1].files
    harness.githost.files_at[HEAD] = {p: c.encode() for p, c in pushed.items()}
    gate(harness, number, mergeable_state="clean", runs=[GREEN])
    pushes = len(harness.githost.pushes)

    r = precheck(harness, token, node_id)
    assert r.status_code == 409, r.text
    assert r.json()["error"] == "node-blocked"
    assert r.json()["details"]["unproved_deps"] == ["and-reassoc"]
    assert len(harness.githost.pushes) == pushes and not harness.githost.dispatches
