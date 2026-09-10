"""Precheck refusals not yet named by a test (F06-R1, R2, R5, R6, R10; C7, C8).

Most of these are results the scratch repository could hand back that the service must not
serve: a run for the wrong runner, a result for another bundle, a signature block whose kind is
not ``service``, or an artifact that is not a result at all. Each becomes a job in state
``error`` naming the cause, and none of them yields an attestation a submission could attach.
"""

from __future__ import annotations

import io
import json
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import pytest
from api_fakes import (
    TUTORIAL_NODE,
    TUTORIAL_PROOF,
    FakeGitHost,
    Harness,
    PrecheckKey,
    make_harness,
    make_precheck_key,
    result_zip,
)

from opn_api import precheck
from opn_api.githost import GitHostError

NODE = "and-reassoc"
PREFIX = "targets/propositional/nodes/"


@pytest.fixture(scope="module")
def key(tmp_path_factory: pytest.TempPathFactory) -> PrecheckKey:
    return make_precheck_key(tmp_path_factory.mktemp("precheck-key"))


def bundle_for(node: str = TUTORIAL_NODE) -> dict[str, str]:
    return {f"{PREFIX}{node}/Proof.lean": TUTORIAL_PROOF}


def start(h: Harness, node: str = TUTORIAL_NODE, token: str | None = None) -> str:
    headers = h.auth(token) if token else {}
    r = h.client.post(
        "/precheck", json={"node_id": node, "bundle": bundle_for(node)}, headers=headers
    )
    assert r.status_code == 202, r.text
    return str(r.json()["id"])


def good_zip(h: Harness, job_id: str, key: PrecheckKey | None, **overrides: Any) -> bytes:
    job = precheck.load(h.context, job_id)
    assert job is not None
    fields: dict[str, Any] = {
        "job_id": job.id,
        "node_id": job.node_id,
        "graph_commit": job.graph_commit,
        "bundle_digest": job.bundle_digest,
        "key": key,
    }
    return result_zip(**{**fields, **overrides})


def rezip(zipped: bytes, mutate: Callable[[dict[str, Any]], dict[str, Any]]) -> bytes:
    """The same artifact with ``result.json`` altered after signing."""
    with zipfile.ZipFile(io.BytesIO(zipped)) as archive:
        result = json.loads(archive.read("result.json"))
    return zip_of(json.dumps(mutate(result)).encode())


def zip_of(result_bytes: bytes, name: str = "result.json") -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(name, result_bytes)
    return buffer.getvalue()


def finish_with(h: Harness, job_id: str, artifact: bytes) -> dict[str, Any]:
    h.githost.finish_run(f"job/{job_id}", artifact=(f"result-{job_id}", artifact))
    doc: dict[str, Any] = h.client.get(f"/precheck/{job_id}").json()
    return doc


# --- the route (R1, R2) --------------------------------------------------------------------------


def test_missing_or_malformed_bundle_is_a_400_before_any_job(harness: Harness) -> None:
    for body in (
        {"node_id": TUTORIAL_NODE},
        {"node_id": TUTORIAL_NODE, "bundle": {}},
        {"node_id": TUTORIAL_NODE, "bundle": "theorem x : True := trivial"},
        {"node_id": TUTORIAL_NODE, "bundle": {f"{PREFIX}{TUTORIAL_NODE}/Proof.lean": None}},
    ):
        r = harness.client.post("/precheck", json=body)
        assert r.status_code == 400, body
        assert r.json()["error"] == "bundle-invalid", body
    assert harness.store.jobs == {}
    assert harness.githost.pushes == []


def test_node_id_of_the_wrong_type_is_400(harness: Harness) -> None:
    for node_id in (7, ["tutorial-and-swap"], ""):
        r = harness.client.post("/precheck", json={"node_id": node_id, "bundle": bundle_for()})
        assert r.status_code == 400, node_id
        assert r.json()["error"] == "node-id-missing", node_id


def test_bad_bearer_on_the_tutorial_node_is_401_not_anonymous(harness: Harness) -> None:
    """R2: the anonymous carve-out is for *no* bearer. A bearer that does not resolve is a 401,
    never silently downgraded to an anonymous job with a nonce."""
    r = harness.client.post(
        "/precheck",
        json={"node_id": TUTORIAL_NODE, "bundle": bundle_for()},
        headers=harness.auth("not-a-token"),
    )
    assert r.status_code == 401
    assert r.json()["error"] == "invalid-token"
    assert harness.store.jobs == {}


def test_authenticated_tutorial_precheck_is_charged_to_the_identity_not_the_address() -> None:
    """R2, R8: with a token the tutorial node is an ordinary precheck — the per-address
    anonymous limit does not apply, the per-identity one does."""
    h = make_harness(
        {"OPN_API_ANONYMOUS_PRECHECKS_PER_DAY": "1", "OPN_API_PRECHECKS_PER_HOUR": "2"}
    )
    token = h.token_for("code_alice", "alice-p")
    headers = {**h.auth(token), "X-Forwarded-For": "203.0.113.9"}
    for _ in range(2):
        r = h.client.post(
            "/precheck", json={"node_id": TUTORIAL_NODE, "bundle": bundle_for()}, headers=headers
        )
        assert r.status_code == 202, r.text
        assert "nonce" not in r.json()
    over = h.client.post(
        "/precheck", json={"node_id": TUTORIAL_NODE, "bundle": bundle_for()}, headers=headers
    )
    assert over.status_code == 429
    # The address's own anonymous allowance is untouched by the three above.
    anonymous = h.client.post(
        "/precheck",
        json={"node_id": TUTORIAL_NODE, "bundle": bundle_for()},
        headers={"X-Forwarded-For": "203.0.113.9"},
    )
    assert anonymous.status_code == 202


def test_graph_without_a_rendered_from_commit_is_503(harness: Harness) -> None:
    """Q10: a job pins ``rendered_from``; without one there is nothing to pin to (C7)."""
    doc = json.loads(harness.githost.files["frontier.json"])
    del doc["rendered_from"]
    harness.githost.files["frontier.json"] = json.dumps(doc).encode()
    harness.context.files.pop("frontier.json", None)
    r = harness.client.post("/precheck", json={"node_id": TUTORIAL_NODE, "bundle": bundle_for()})
    assert r.status_code == 503
    assert r.json()["error"] == "graph-unrendered"
    assert harness.store.jobs == {}
    assert harness.githost.pushes == []


def test_a_rate_limited_precheck_creates_no_job_and_pushes_nothing() -> None:
    h = make_harness({"OPN_API_ANONYMOUS_PRECHECKS_PER_DAY": "1"})
    assert (
        h.client.post(
            "/precheck", json={"node_id": TUTORIAL_NODE, "bundle": bundle_for()}
        ).status_code
        == 202
    )
    over = h.client.post("/precheck", json={"node_id": TUTORIAL_NODE, "bundle": bundle_for()})
    assert over.status_code == 429
    assert len(h.store.jobs) == 1
    assert len(h.githost.pushes) == 1


# --- results the service must not serve (R5, R6) ------------------------------------------------


def test_result_for_a_local_runner_is_refused(harness: Harness, key: PrecheckKey) -> None:
    """R6: the attestation must say ``runner: hosted``; a local run is not a precheck."""
    harness.commit_precheck_key(key.public)
    job_id = start(harness)
    doc = finish_with(harness, job_id, good_zip(harness, job_id, key, runner="local"))
    assert doc["state"] == "error"
    assert "runner" in doc["error"]
    assert "result" not in doc


def test_result_for_another_bundle_is_refused(harness: Harness, key: PrecheckKey) -> None:
    """R6: a passing result over different bytes must not be served for this job's bundle."""
    harness.commit_precheck_key(key.public)
    job_id = start(harness)
    doc = finish_with(harness, job_id, good_zip(harness, job_id, key, bundle_digest="e" * 64))
    assert doc["state"] == "error"
    assert "bundle digest" in doc["error"]


def test_signature_of_another_kind_is_refused_even_when_it_verifies(
    harness: Harness, key: PrecheckKey
) -> None:
    """R6: the block must say ``kind: service``. The signature covers everything but the
    signature block, so relabelling the kind leaves a valid signature — and it is still refused,
    because a precheck claiming to be the authoritative gate is exactly the confusion D-28
    forbids."""
    harness.commit_precheck_key(key.public)
    job_id = start(harness)

    def relabel(result: dict[str, Any]) -> dict[str, Any]:
        result["attestation"]["signature"]["kind"] = "gate"
        return result

    doc = finish_with(harness, job_id, rezip(good_zip(harness, job_id, key), relabel))
    assert doc["state"] == "error"
    assert "'gate'" in doc["error"] and "service" in doc["error"]


def test_result_without_an_attestation_is_refused(harness: Harness, key: PrecheckKey) -> None:
    harness.commit_precheck_key(key.public)
    job_id = start(harness)

    def strip(result: dict[str, Any]) -> dict[str, Any]:
        del result["attestation"]
        return result

    doc = finish_with(harness, job_id, rezip(good_zip(harness, job_id, key), strip))
    assert doc["state"] == "error"
    assert "no attestation" in doc["error"]


def test_attestation_naming_an_unknown_schema_is_refused(
    harness: Harness, key: PrecheckKey
) -> None:
    harness.commit_precheck_key(key.public)
    job_id = start(harness)

    def future(result: dict[str, Any]) -> dict[str, Any]:
        result["attestation"]["schema"] = "attestation/v99"
        return result

    doc = finish_with(harness, job_id, rezip(good_zip(harness, job_id, key), future))
    assert doc["state"] == "error"
    assert "attestation/v99" in doc["error"]


def test_attestation_that_fails_its_schema_is_refused(harness: Harness, key: PrecheckKey) -> None:
    harness.commit_precheck_key(key.public)
    job_id = start(harness)

    def corrupt(result: dict[str, Any]) -> dict[str, Any]:
        result["attestation"]["verdict"] = "maybe"
        return result

    doc = finish_with(harness, job_id, rezip(good_zip(harness, job_id, key), corrupt))
    assert doc["state"] == "error"
    assert "does not validate" in doc["error"]


@pytest.mark.parametrize(
    ("label", "artifact", "fragment"),
    [
        ("not a zip", b"PK\x03\x04 but not really", "not a readable zip"),
        ("zip without result.json", zip_of(b"{}", name="other.json"), "no result.json"),
        ("result.json is not JSON", zip_of(b"{"), "not valid JSON"),
        ("result.json is a list", zip_of(b"[]"), "not a JSON object"),
        ("oversized result", zip_of(b" " * precheck.MAX_RESULT_BYTES + b"{}"), "limit"),
    ],
)
def test_artifact_that_is_not_a_result_is_an_error_naming_why(
    harness: Harness, key: PrecheckKey, label: str, artifact: bytes, fragment: str
) -> None:
    """§6, R5: the artifact is untrusted bytes from a public repository; each malformation is
    named, and none becomes a served result."""
    harness.commit_precheck_key(key.public)
    job_id = start(harness)
    doc = finish_with(harness, job_id, artifact)
    assert doc["state"] == "error", label
    assert fragment in doc["error"], (label, doc["error"])
    assert "result" not in doc


@dataclass
class HostWithoutArtifacts(FakeGitHost):
    """A host whose artifact download fails the way a blob-storage outage would."""

    download_failure: str | None = None

    def download_artifact(self, repo: str, run_id: int, name: str) -> bytes | None:
        if self.download_failure:
            raise GitHostError(self.download_failure)
        return super().download_artifact(repo, run_id, name)


def test_download_failure_leaves_the_job_unfinished_not_errored(key: PrecheckKey) -> None:
    """C7: a transient failure to fetch the artifact is an outage, not a verdict — the job keeps
    its state and completes on the next poll once the host answers."""
    host = HostWithoutArtifacts.with_fixtures()
    assert isinstance(host, HostWithoutArtifacts)
    h = make_harness(githost=host)
    h.commit_precheck_key(key.public)
    job_id = start(h)
    host.finish_run(f"job/{job_id}", artifact=(f"result-{job_id}", good_zip(h, job_id, key)))
    host.download_failure = "GET /actions/artifacts/1/zip failed: ReadTimeout"
    doc = h.client.get(f"/precheck/{job_id}").json()
    assert doc["state"] == "queued"
    assert "error" not in doc
    job = precheck.load(h.context, job_id)
    assert job is not None and job.state == "queued" and job.error is None

    host.download_failure = None
    assert h.client.get(f"/precheck/{job_id}").json()["state"] == "done"


def test_an_error_job_is_terminal(harness: Harness, key: PrecheckKey) -> None:
    """R5: once a job is ``error``, a later good artifact on the same branch changes nothing."""
    harness.commit_precheck_key(key.public)
    job_id = start(harness)
    assert finish_with(harness, job_id, b"garbage")["state"] == "error"
    doc = finish_with(harness, job_id, good_zip(harness, job_id, key))
    assert doc["state"] == "error"
    assert "result" not in doc


def test_precheck_response_never_carries_the_bundle_or_the_proof(harness: Harness) -> None:
    """R11, §7: the bundle is public on the scratch repository, not echoed by the service."""
    r = harness.client.post("/precheck", json={"node_id": TUTORIAL_NODE, "bundle": bundle_for()})
    assert TUTORIAL_PROOF not in r.text
    got = harness.client.get(f"/precheck/{r.json()['id']}")
    assert TUTORIAL_PROOF not in got.text
