"""Finding 4 (2026-09-13, the live MCP contribution; the 2026-09-12 register's #4): the artifact
type and the path it lands at are not checked against each other.

A partial is a ``.lean`` assembly under ``attempts/`` (D-12 #5; ``paths._node_role`` calls that
role ``partial``), and F11 made the submission *be* the ``attempts/<ts>-<pseudonym>-partial.lean``
file (``postmerge.PARTIAL_SUFFIX``). ``POST /submissions`` takes ``artifact_type`` and a bundle
and never compares them: ``artifact_type: partial`` with a ``Proof.lean`` bundle opens the pull
request, and so does ``artifact_type: proof`` with a bundle under ``attempts/``. The tester paid
two prechecks to discover the path by trial; the guide said the gate writes it.

Asserted here (plan Phase 0, F07-T7): the mismatch is a 400 naming the path the type belongs at,
before any pull request is opened, using the gate's own role of the path (``opn_gate.paths``).
The un-marked test pins the right pairing, which the service accepts today and must keep
accepting. Held as strict xfails until F07-T7's service half landed (2026-09-14), when the
marks came off.
"""

from __future__ import annotations

from typing import Any

import pytest
from api_fakes import (
    PROOF_PREFIX,
    TUTORIAL_NODE,
    TUTORIAL_PROOF,
    Harness,
    PrecheckKey,
    make_precheck_key,
    result_zip,
)

PROOF_PATH = f"{PROOF_PREFIX}{TUTORIAL_NODE}/Proof.lean"
PARTIAL_PATH = f"{PROOF_PREFIX}{TUTORIAL_NODE}/attempts/20260913T160800Z-alice-partial.lean"
FINDING_4 = "finding 4 (F07-R1, F11-Q28, D-12): {}; fix: F07-T7 (Mike, 2026-09-13)"


@pytest.fixture(scope="module")
def key(tmp_path_factory: pytest.TempPathFactory) -> PrecheckKey:
    return make_precheck_key(tmp_path_factory.mktemp("precheck-key"))


def passing_job(h: Harness, key: PrecheckKey, token: str, bundle: dict[str, str]) -> str:
    """A done, passing precheck of ``bundle`` by the token's identity — ``Harness.tutorial_job``
    over a bundle of the test's choosing. Returns the job id a submission binds to (F07-R1)."""
    h.commit_precheck_key(key.public)
    created = h.client.post(
        "/precheck", json={"node_id": TUTORIAL_NODE, "bundle": bundle}, headers=h.auth(token)
    )
    assert created.status_code == 202, created.text  # guard: the precheck takes this bundle
    doc: dict[str, Any] = created.json()
    artifact = result_zip(
        job_id=doc["id"],
        node_id=TUTORIAL_NODE,
        graph_commit=doc["graph_commit"],
        bundle_digest=doc["bundle_digest"],
        key=key,
    )
    h.githost.finish_run(f"job/{doc['id']}", artifact=(f"result-{doc['id']}", artifact))
    polled = h.client.get(f"/precheck/{doc['id']}").json()
    assert polled["state"] == "done" and polled["result"]["verdict"] == "pass", polled
    return str(doc["id"])


def submit(h: Harness, token: str, *, artifact_type: str, bundle: dict[str, str], job: str) -> Any:
    body = {
        "node_id": TUTORIAL_NODE,
        "artifact_type": artifact_type,
        "bundle": bundle,
        "precheck_job_id": job,
    }
    return h.client.post("/submissions", json=body, headers=h.auth(token))


def test_a_partial_may_not_be_filed_as_proof_lean(harness: Harness, key: PrecheckKey) -> None:
    """A partial is an ``attempts/<ts>-<pseudonym>-partial.lean`` file (F11-Q28): a bundle
    writing ``Proof.lean`` under ``artifact_type: partial`` is a 400 whose message says where
    a partial goes, and nothing is pushed."""
    token = harness.token_for("code_alice", "alice")
    job = passing_job(harness, key, token, {PROOF_PATH: TUTORIAL_PROOF})
    pushed = len(harness.githost.pushes)  # the precheck's own job branch (F06-R3)
    r = submit(
        harness, token, artifact_type="partial", bundle={PROOF_PATH: TUTORIAL_PROOF}, job=job
    )
    assert r.status_code == 400, f"a partial at Proof.lean was accepted: {r.status_code} {r.text}"
    message = r.json()["message"]
    assert "attempts/" in message and "-partial.lean" in message, message
    assert len(harness.githost.pushes) == pushed
    assert harness.githost.pulls == []


def test_a_proof_may_not_be_filed_under_attempts(harness: Harness, key: PrecheckKey) -> None:
    """A proof is ``nodes/<id>/Proof.lean`` (D-3): a bundle under ``attempts/`` with
    ``artifact_type: proof`` is a 400 naming ``Proof.lean``, and nothing is pushed."""
    token = harness.token_for("code_alice", "alice")
    job = passing_job(harness, key, token, {PARTIAL_PATH: TUTORIAL_PROOF})
    pushed = len(harness.githost.pushes)  # the precheck's own job branch (F06-R3)
    r = submit(
        harness, token, artifact_type="proof", bundle={PARTIAL_PATH: TUTORIAL_PROOF}, job=job
    )
    assert r.status_code == 400, f"a proof under attempts/ was accepted: {r.status_code} {r.text}"
    assert "Proof.lean" in r.json()["message"], r.text
    assert len(harness.githost.pushes) == pushed
    assert harness.githost.pulls == []


def test_pin_a_partial_under_attempts_is_accepted(harness: Harness, key: PrecheckKey) -> None:
    """**PIN — the pairing the fix must keep.** ``artifact_type: partial`` with the bundle at
    ``attempts/<ts>-<pseudonym>-partial.lean`` opens the pull request today, with exactly that
    file in the diff (F11-Q28: the submission *is* the attempts file)."""
    token = harness.token_for("code_alice", "alice")
    job = passing_job(harness, key, token, {PARTIAL_PATH: TUTORIAL_PROOF})
    r = submit(
        harness, token, artifact_type="partial", bundle={PARTIAL_PATH: TUTORIAL_PROOF}, job=job
    )
    assert r.status_code == 201, r.text
    assert r.json()["artifact_type"] == "partial"
    push = harness.githost.pushes[-1]  # the one before it is the precheck's job branch
    assert push.repo == harness.settings.graph_repo
    assert push.files == {PARTIAL_PATH: TUTORIAL_PROOF}
    [pr] = harness.githost.pulls
    assert pr.head == push.branch and pr.title == f"partial: {TUTORIAL_NODE}"


# --- edges (F07-T7 service half, 2026-09-14) ------------------------------------------------------

POSTMORTEM_PATH = f"{PROOF_PREFIX}{TUTORIAL_NODE}/attempts/20260913T160800Z-alice.yaml"
POSTMORTEM_TEXT = "schema: postmortem/v1\n"


def test_a_two_file_partial_carrying_proof_lean_is_refused(
    harness: Harness, key: PrecheckKey
) -> None:
    """A partial bundle with the assembly *and* ``Proof.lean`` is not a partial the gate knows
    (``modes._mode_for``: a proof role beside a partial is no mode), so it is refused like the
    single-file case, naming where a partial goes."""
    token = harness.token_for("code_alice", "alice")
    two = {PARTIAL_PATH: TUTORIAL_PROOF, PROOF_PATH: TUTORIAL_PROOF}
    job = passing_job(harness, key, token, two)
    pushed = len(harness.githost.pushes)
    r = submit(harness, token, artifact_type="partial", bundle=two, job=job)
    assert r.status_code == 400, r.text
    assert r.json()["error"] == "artifact-path-mismatch", r.text
    assert "-partial.lean" in r.json()["message"], r.text
    assert len(harness.githost.pushes) == pushed
    assert harness.githost.pulls == []


def test_a_two_file_partial_with_an_append_is_accepted(harness: Harness, key: PrecheckKey) -> None:
    """**PIN.** The gate's partial mode takes appends beside the assembly; the service must not be
    stricter than the gate, so the assembly plus a postmortem opens the pull request."""
    token = harness.token_for("code_alice", "alice")
    two = {PARTIAL_PATH: TUTORIAL_PROOF, POSTMORTEM_PATH: POSTMORTEM_TEXT}
    job = passing_job(harness, key, token, two)
    r = submit(harness, token, artifact_type="partial", bundle=two, job=job)
    assert r.status_code == 201, r.text
    assert harness.githost.pushes[-1].files == two


@pytest.mark.parametrize(
    ("artifact_type", "path", "names"),
    [
        ("reduction", PROOF_PATH, "-partial.lean"),  # a one-hole partial lands where a partial does
        ("counterexample", PARTIAL_PATH, "Proof.lean"),  # a certificate is Proof.lean (D-12)
        ("vacuity", PARTIAL_PATH, "Proof.lean"),
    ],
)
def test_the_other_kinds_follow_their_path(
    harness: Harness, key: PrecheckKey, artifact_type: str, path: str, names: str
) -> None:
    token = harness.token_for("code_alice", "alice")
    job = passing_job(harness, key, token, {path: TUTORIAL_PROOF})
    r = submit(harness, token, artifact_type=artifact_type, bundle={path: TUTORIAL_PROOF}, job=job)
    assert r.status_code == 400, r.text
    assert names in r.json()["message"], r.text
    assert harness.githost.pulls == []


def test_a_partial_with_only_an_append_is_refused(harness: Harness, key: PrecheckKey) -> None:
    """A partial bundle with no assembly at all carries nothing to be a partial of."""
    token = harness.token_for("code_alice", "alice")
    only = {POSTMORTEM_PATH: POSTMORTEM_TEXT}
    job = passing_job(harness, key, token, only)
    r = submit(harness, token, artifact_type="partial", bundle=only, job=job)
    assert r.status_code == 400, r.text
    assert "-partial.lean" in r.json()["message"], r.text
