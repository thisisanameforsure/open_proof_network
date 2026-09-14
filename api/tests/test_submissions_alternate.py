"""F07-T12: where a proof lands depends on whether the node is proved (R7; AC25; D-25 v3.13).

``POST /submissions`` refuses, before any precheck binding and before anything is pushed, the two
placements the gate would refuse: a ``Proof.lean`` on a node whose proof has merged (outside the
tutorial node, which D-27 keeps open to rehearsal), and an alternate on a node with no proof. An
alternate on a proved node opens its pull request with exactly that file.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from api_fakes import (
    PROOF_PREFIX,
    TUTORIAL_PROOF,
    Harness,
    PrecheckKey,
    make_precheck_key,
    result_zip,
)

GRAPH_JSON = "targets/propositional/graph.json"
ALTERNATE = "attempts/20260914T120000Z-alice-alternate.lean"


@pytest.fixture(scope="module")
def key(tmp_path_factory: pytest.TempPathFactory) -> PrecheckKey:
    return make_precheck_key(tmp_path_factory.mktemp("precheck-key"))


def mark_proved(h: Harness) -> tuple[str, str]:
    """Commit a graph.json in which one non-tutorial node is proved; answer (proved, unproved)."""
    doc: dict[str, Any] = json.loads(h.githost.files[GRAPH_JSON])
    others = [n for n in doc["nodes"] if not n["tutorial"]]
    assert len(others) >= 2  # guard: the fixture has two non-tutorial nodes to use
    proved, unproved = others[0], others[1]
    proved["proof_commit"] = "8" * 40
    unproved["proof_commit"] = None
    h.githost.files[GRAPH_JSON] = json.dumps(doc).encode("utf-8")
    h.context.files.pop(GRAPH_JSON, None)
    return str(proved["node_id"]), str(unproved["node_id"])


def passing_job(h: Harness, key: PrecheckKey, token: str, node: str, bundle: dict[str, str]) -> str:
    """A done, passing precheck of ``bundle`` on ``node`` by the token's identity."""
    h.commit_precheck_key(key.public)
    created = h.client.post(
        "/precheck", json={"node_id": node, "bundle": bundle}, headers=h.auth(token)
    )
    assert created.status_code == 202, created.text  # guard: the precheck takes this bundle
    doc: dict[str, Any] = created.json()
    artifact = result_zip(
        job_id=doc["id"],
        node_id=node,
        graph_commit=doc["graph_commit"],
        bundle_digest=doc["bundle_digest"],
        key=key,
    )
    h.githost.finish_run(f"job/{doc['id']}", artifact=(f"result-{doc['id']}", artifact))
    return str(doc["id"])


def submit(h: Harness, token: str, node: str, bundle: dict[str, str], job: str) -> Any:
    body = {"node_id": node, "artifact_type": "proof", "bundle": bundle, "precheck_job_id": job}
    return h.client.post("/submissions", json=body, headers=h.auth(token))


def test_alternate_pairing(harness: Harness, key: PrecheckKey) -> None:
    """AC25: Proof.lean on a proved node is a 400 naming the alternate path; an alternate on an
    unproved node is a 400; neither pushes anything. An alternate on a proved node opens."""
    token = harness.token_for("code_alice", "alice")
    proved, unproved = mark_proved(harness)
    pushed = len(harness.githost.pushes)

    replaced = submit(
        harness, token, proved, {f"{PROOF_PREFIX}{proved}/Proof.lean": TUTORIAL_PROOF}, "nojob"
    )
    assert replaced.status_code == 400, replaced.text
    assert replaced.json()["error"] == "proof-replaces-merged", replaced.text
    assert f"{proved}/attempts/<ts>-<pseudonym>-alternate.lean" in replaced.json()["message"]

    early = submit(
        harness, token, unproved, {f"{PROOF_PREFIX}{unproved}/{ALTERNATE}": TUTORIAL_PROOF}, "nojob"
    )
    assert early.status_code == 400, early.text
    assert early.json()["error"] == "alternate-unproved", early.text
    assert len(harness.githost.pushes) == pushed and harness.githost.pulls == []

    bundle = {f"{PROOF_PREFIX}{proved}/{ALTERNATE}": TUTORIAL_PROOF}
    job = passing_job(harness, key, token, proved, bundle)
    opened = submit(harness, token, proved, bundle, job)
    assert opened.status_code == 201, opened.text
    push = harness.githost.pushes[-1]
    assert push.files == bundle
    [pr] = harness.githost.pulls
    assert pr.head == push.branch
