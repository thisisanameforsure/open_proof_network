"""Round four of failing-case coverage for the api: the last unexercised lines, one failing case
each, named by what it proves (session note 2026-09-10-test-coverage-review.md for rounds one to
three).

One line is left alone on purpose: ``submissions.py:217`` (``precheck-node-differs``) is
unreachable, because a job's bundle digest is over the bundle's paths and every path in a bundle
must lie under its claim's node (``opn_gate.paths._offence``) — a job for another node cannot
have the same digest as a bundle validated for this one. Noted rather than forced.
"""

from __future__ import annotations

import base64
import os
from datetime import UTC
from pathlib import Path
from typing import Any

import boto3
import pytest
import samples
from api_fakes import (
    TEST_ENV,
    TUTORIAL_NODE,
    FakeClock,
    FakeGitHost,
    Harness,
    PrecheckKey,
    make_harness,
    make_precheck_key,
)
from precheck.job import sign_service
from starlette.testclient import TestClient

from opn_api import bundles, clock, config, frontier, identity, precheck, sshsig
from opn_api import store as storemod
from opn_api.app import create_app
from opn_api.store import Claim as ClaimRecord
from opn_api.store import Identity, MemoryStore
from opn_gate.paths import Claim
from opn_gate.signer import NAMESPACE

TARGET = "propositional"
NODE = "and-reassoc"
PREFIX = f"targets/{TARGET}/nodes/"
PROOF = "import Nodes.X.Context\n\ntheorem x : True := trivial\n"
PAYLOAD = b'{"schema": "attestation/v4", "verdict": "pass"}'


def armor(blob: bytes) -> str:
    return f"{sshsig.ARMOR_BEGIN}\n{base64.b64encode(blob).decode()}\n{sshsig.ARMOR_END}\n"


def key_line(blob: bytes) -> str:
    return f"ssh-ed25519 {base64.b64encode(blob).decode()} comment"


# --- sshsig: the wire-format refusals a truncation never happens to hit (F06-R5, R6; C7) ---------


def test_a_key_blob_too_short_for_a_length_prefix_is_truncated_not_indexed() -> None:
    """Two bytes cannot hold the four-byte length of the algorithm string: the reader names the
    truncation rather than raising a struct error out of the seam."""
    with pytest.raises(sshsig.SshsigError, match="truncated: no length prefix"):
        sshsig.fingerprint(key_line(b"\x00\x00"))


def test_a_key_blob_of_another_algorithm_behind_an_ed25519_label_is_refused() -> None:
    """The line says ``ssh-ed25519`` but the blob's own algorithm string says otherwise: the
    blob is the authority, and only ed25519 is accepted (C8 items 1 and 2)."""
    blob = sshsig._string(b"ssh-rsa") + sshsig._string(b"\x01\x00\x01")
    with pytest.raises(sshsig.SshsigError, match="unsupported key algorithm b'ssh-rsa'"):
        sshsig.fingerprint(key_line(blob))


def test_an_armored_blob_without_the_sshsig_preamble_is_refused_before_any_key_is_read() -> None:
    """Valid armor around bytes that are not a signature: the preamble check answers first, so
    the committed key is never consulted (the key argument here is deliberately not one)."""
    with pytest.raises(sshsig.SshsigError, match="no SSHSIG preamble"):
        sshsig.verify(PAYLOAD, armor(b"NOTSIG" + b"\x00" * 8), "", namespace=NAMESPACE)


def test_an_sshsig_preamble_with_no_room_for_a_version_is_refused() -> None:
    with pytest.raises(sshsig.SshsigError, match="has no version"):
        sshsig.verify(PAYLOAD, armor(sshsig.MAGIC + b"\x00\x01"), "", namespace=NAMESPACE)


# --- bundles: shapes git never produces, and a bundle with no proof (F06-R1) --------------------


def test_a_rejection_renders_as_the_400_body_with_its_details_flattened() -> None:
    rejection = bundles.Rejection("path-invalid", "why", {"path": "p", "limit": 3})
    assert rejection.as_dict() == {
        "error": "path-invalid",
        "message": "why",
        "path": "p",
        "limit": 3,
    }


def test_a_path_longer_than_the_cap_is_refused_naming_the_cap() -> None:
    long = f"{PREFIX}{NODE}/attempts/{'x' * bundles.MAX_PATH_LENGTH}.yaml"
    bundle, rejection = bundles.validate({long: "schema: postmortem/v1\n"}, Claim(TARGET, NODE))
    assert bundle is None and rejection is not None
    assert rejection.code == "path-invalid"
    assert f"longer than {bundles.MAX_PATH_LENGTH}" in rejection.message
    assert len(rejection.details["path"]) == bundles.MAX_PATH_LENGTH


def test_a_path_padded_with_whitespace_is_refused_as_a_shape_not_a_permission() -> None:
    """`` targets/...`` is not outside the node — it is not a path git would name at all."""
    bundle, rejection = bundles.validate(
        {f" {PREFIX}{NODE}/Proof.lean": PROOF}, Claim(TARGET, NODE)
    )
    assert bundle is None and rejection is not None
    assert rejection.code == "path-invalid" and "padded with whitespace" in rejection.message


def test_a_bundle_of_appends_only_has_an_empty_proof_text() -> None:
    """The proof is found by its path, after any append that sorts before it; a bundle with no
    Proof.lean at all reports an empty proof rather than the first file's content."""
    claim = Claim(TARGET, NODE)
    postmortem = f"{PREFIX}{NODE}/attempts/2026-09-09.yaml"
    appends_only, rejection = bundles.validate({postmortem: "schema: postmortem/v1\n"}, claim)
    assert rejection is None and appends_only is not None
    assert appends_only.proof_text == ""
    both, rejection = bundles.validate(
        {postmortem: "schema: postmortem/v1\n", f"{PREFIX}{NODE}/Proof.lean": PROOF}, claim
    )
    assert rejection is None and both is not None
    assert next(iter(both.files)) == postmortem and both.proof_text == PROOF


# --- app: the store the settings name cannot be built (F05-R13; C7) -----------------------------


def test_a_store_that_cannot_be_built_serves_503_naming_the_failure_not_a_traceback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """R13: an unbuildable store is one more missing thing on ``/health`` (by exception type,
    never its message — C8) and the app still comes up, over a memory store that serves nothing."""

    def unbuildable(settings: config.Settings) -> Any:
        raise RuntimeError("secret-bearing message that must not be served")

    monkeypatch.setattr(storemod, "build", unbuildable)
    app = create_app(config.load(TEST_ENV), githost=FakeGitHost.with_fixtures(), clock=FakeClock())
    assert isinstance(app.state.context.store, MemoryStore)
    client = TestClient(app)
    health = client.get("/health")
    assert health.status_code == 503
    assert health.json()["missing"] == ["store (RuntimeError)"]
    assert "secret-bearing" not in health.text
    assert client.get("/frontier.json").status_code == 503


# --- appends: a declared tooling string lands in the annex front matter (D-23, D-31) -------------


def test_a_declared_tooling_string_lands_in_the_annex_and_a_non_string_is_refused(
    harness: Harness,
) -> None:
    token = harness.token_for("code_alice", "alice")
    body = {"node_id": TUTORIAL_NODE, "text": "prose\n", "model_and_tooling": "claude-fable-5-1"}
    r = harness.client.post("/annexes", json=body, headers=harness.auth(token))
    assert r.status_code == 201, r.text
    push = harness.githost.pushes[-1]
    (content,) = push.files.values()
    assert "model_and_tooling: claude-fable-5-1\n" in content
    refused = harness.client.post(
        "/annexes", json={**body, "model_and_tooling": 3}, headers=harness.auth(token)
    )
    assert refused.status_code == 400 and refused.json()["error"] == "tooling-invalid"
    assert len(harness.githost.pushes) == 1


# --- config: the Lambda's parameter source, with and without a client (F05-R13) -----------------


def test_load_parameters_builds_an_ssm_client_when_given_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The handler passes no client: boto3's is built for ``ssm`` and paged like any other."""
    built: list[str] = []

    class Ssm:
        def get_parameters_by_path(self, **kwargs: Any) -> dict[str, Any]:
            assert kwargs == {"Path": "/opn/api/", "WithDecryption": True}
            return {"Parameters": [{"Name": "/opn/api/token-secret", "Value": "s3"}]}

    def client(service: str) -> Ssm:
        built.append(service)
        return Ssm()

    monkeypatch.setattr(boto3, "client", client)
    assert config.load_parameters("/opn/api/") == {"OPN_API_TOKEN_SECRET": "s3"}
    assert built == ["ssm"]


def test_environment_with_parameters_lets_a_parameter_override_the_process_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    variable = config.PARAMETERS["token-secret"]
    from_env, from_store = "from-env", "from-/p/"
    monkeypatch.setenv(variable, from_env)
    monkeypatch.setenv("OPN_API_LOG_LEVEL", "DEBUG")
    monkeypatch.setattr(config, "load_parameters", lambda prefix: {variable: f"from-{prefix}"})
    merged = config.environment_with_parameters("/p/")
    assert merged[variable] == from_store
    assert merged["OPN_API_LOG_LEVEL"] == "DEBUG"
    assert os.environ[variable] == from_env  # the process is not rewritten


# --- identity: the browser's form, with and without the DCO (F05-R4, Q4) -----------------------


def proof_id_for(h: Harness, code: str) -> str:
    start = h.client.get("/auth/github/start", follow_redirects=False)
    state = start.headers["location"].split("state=")[1].split("&")[0]
    cb = h.client.get(
        "/auth/github/callback",
        params={"code": code, "state": state},
        headers={"Accept": "application/json"},
    )
    assert cb.status_code == 200, cb.text
    return str(cb.json()["proof"]["id"])


def test_a_form_that_never_ticks_the_dco_is_refused_and_no_identity_is_made(
    harness: Harness,
) -> None:
    """A form without any ``dco.*`` field nests to a body with no ``dco`` at all, which is the
    same refusal as an unticked box (R4), not a key error."""
    form = {
        "proof.kind": identity.PROOF_GITHUB,
        "proof.id": proof_id_for(harness, "code_alice"),
        "pseudonym": "human",
    }
    r = harness.client.post("/tokens", data=form)
    assert r.status_code == 400 and r.json()["error"] == "dco-not-accepted"
    assert harness.store.identities == {}


def test_a_browser_form_gets_the_token_page_and_an_agent_gets_json(harness: Harness) -> None:
    """Q4: a form post without ``Accept: application/json`` is answered with the escaped HTML
    page carrying the token once; the same fields as JSON are answered as JSON."""
    form = {
        "proof.kind": identity.PROOF_GITHUB,
        "proof.id": proof_id_for(harness, "code_alice"),
        "pseudonym": "human-one",
        "dco.version": identity.DCO_VERSION,
        "dco.accepted": "on",
    }
    page = harness.client.post("/tokens", data=form)
    assert page.status_code == 201, page.text
    assert page.headers["content-type"].startswith("text/html")
    assert "<h1>Token for human-one</h1>" in page.text
    token = page.text.split("<pre>")[1].split("</pre>")[0]
    assert harness.client.get("/claims", headers=harness.auth(token)).status_code != 401

    as_json = harness.client.post(
        "/tokens",
        data={**form, "proof.id": proof_id_for(harness, "code_bob"), "pseudonym": "human-two"},
        headers={"Accept": "application/json"},
    )
    assert as_json.status_code == 201 and as_json.json()["identity"]["pseudonym"] == "human-two"


class VanishingStore(MemoryStore):
    """A store where the tutorial job is gone by the time the pseudonym clash is undone."""

    def put_identity(self, identity: Identity) -> None:
        if identity.proof_kind == "tutorial":
            self.jobs.clear()
        super().put_identity(identity)


def test_undoing_a_spent_nonce_tolerates_a_job_that_has_since_expired(tmp_path: Path) -> None:
    """AC3 on the tutorial path: the nonce is un-spent so the person can pick another pseudonym;
    when the job record is already gone there is nothing to restore, and the 409 still answers."""
    h = make_harness(store=VanishingStore())
    with h.client:
        h.token_for("code_alice", "taken")
        job = h.tutorial_job(make_precheck_key(tmp_path))
        r = h.client.post(
            "/tokens",
            json={
                "proof": {"kind": "tutorial", "job_id": job["id"], "nonce": job["nonce"]},
                "pseudonym": "taken",
                "dco": {"version": identity.DCO_VERSION, "accepted": True},
            },
        )
    assert r.status_code == 409 and r.json()["error"] == "pseudonym-taken"
    assert h.store.jobs == {}


# --- precheck: the job's own views, and a signature the reader cannot parse (F06-R5, R6) --------


def test_a_job_knows_its_claim_and_its_store_key() -> None:
    job = precheck.Job(
        id="01J",
        node_id=NODE,
        target_id=TARGET,
        statement_hash="h",
        graph_commit="c" * 40,
        bundle_digest="d" * 64,
        created="2026-09-10T00:00:00Z",
    )
    assert job.claim == Claim(TARGET, NODE)
    assert precheck.store_key(job.id) == f"{precheck.KEY_JOB}01J"


def test_an_attestation_whose_signature_is_not_sshsig_is_a_result_error_naming_the_reader(
    harness: Harness, tmp_path: Path
) -> None:
    """R5: a malformed signature is the producer's bug, not a wrong key, and the refusal says so
    rather than propagating the reader's exception."""
    key: PrecheckKey = make_precheck_key(tmp_path)
    created = harness.tutorial_job(key)
    job = precheck.load(harness.context, created["id"])
    assert job is not None
    signed = sign_service(
        samples.attestation(node_id=job.node_id, graph_commit=job.graph_commit, runner="hosted"),
        key.private,
    )
    doc = {**signed, "signature": {**signed["signature"], "value": "not an armored block"}}
    with pytest.raises(precheck.ResultError, match=r"signature is malformed: .*armored"):
        precheck.verify_result(harness.context, job, {"attestation": doc})


# --- frontier: one identity, several active claims (F05-R9) --------------------------------------


def test_the_registry_looks_an_identity_up_once_across_its_active_claims(harness: Harness) -> None:
    harness.token_for("code_alice", "alice")
    (identity_id,) = harness.store.identities
    for n, node in enumerate((NODE, TUTORIAL_NODE)):
        harness.store.put_claim(
            ClaimRecord(
                id=f"claim-{n}",
                node_id=node,
                target_id=TARGET,
                identity_id=identity_id,
                created="2026-09-09T12:00:00Z",
                expires="2999-01-01T00:00:00Z",
            )
        )
    looked_up: list[str] = []
    real = harness.store.get_identity

    def counting(identity_id: str) -> Identity | None:
        looked_up.append(identity_id)
        return real(identity_id)

    harness.store.get_identity = counting  # type: ignore[method-assign]
    reg = frontier.registry(harness.context)
    assert {k: [a["pseudonym"] for a in v["active"]] for k, v in reg.items()} == {
        NODE: ["alice"],
        TUTORIAL_NODE: ["alice"],
    }
    assert looked_up == [identity_id]


# --- clock: the system clock is UTC at second precision ------------------------------------------


def test_the_system_clock_answers_utc_seconds() -> None:
    now = clock.SystemClock().now()
    assert now.tzinfo is UTC and now.microsecond == 0
    assert clock.parse(clock.render(now)) == now
