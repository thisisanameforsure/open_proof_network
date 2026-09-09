"""F06-T1, T3: bundles, jobs, the two routes, and the dispatch/poll/retrieve state machine
(R1-R3, R5, R6, R8, R10; AC1-AC3, AC4-AC9, AC12)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from api_fakes import Harness, PrecheckKey, make_harness, make_precheck_key, result_zip

from opn_api import bundles, precheck
from opn_gate.paths import Claim

NODE = "and-reassoc"
TUTORIAL = "tutorial-and-swap"
PROVED_TUTORIAL = "already-proved"
TARGET = "propositional"
PREFIX = f"targets/{TARGET}/nodes/"

PROOF = "import Nodes.X.Context\n\ntheorem x : True := trivial\n"


def bundle_for(node: str = NODE, **extra: str) -> dict[str, str]:
    return {f"{PREFIX}{node}/Proof.lean": PROOF, **extra}


def post(h: Harness, body: dict[str, Any], token: str | None = None) -> Any:
    headers = h.auth(token) if token else {}
    return h.client.post("/precheck", json=body, headers=headers)


# --- bundle validation, as a pure function (R1) --------------------------------------------------


def test_bundle_path_rejected() -> None:
    """AC1: a bundle touching Statement.lean is refused, naming the path, before any job."""
    claim = Claim(TARGET, NODE)
    bundle, rejection = bundles.validate(
        {f"{PREFIX}{NODE}/Statement.lean": "theorem x : True := sorry\n"}, claim
    )
    assert bundle is None
    assert rejection is not None
    assert rejection.code == "path-forbidden"
    assert "Statement.lean" in rejection.message


def test_bundle_size_cap() -> None:
    """AC2: 600 KiB is refused naming the limit."""
    claim = Claim(TARGET, NODE)
    big = {f"{PREFIX}{NODE}/Proof.lean": "-- x\n" * (600 * 1024 // 5)}
    bundle, rejection = bundles.validate(big, claim)
    assert bundle is None
    assert rejection is not None
    assert rejection.code == "bundle-too-large"
    assert rejection.details["limit"] == bundles.MAX_BUNDLE_BYTES
    assert rejection.details["size"] > bundles.MAX_BUNDLE_BYTES


def test_bundle_accepts_a_proof_and_appends() -> None:
    claim = Claim(TARGET, NODE)
    bundle, rejection = bundles.validate(
        bundle_for(NODE, **{f"{PREFIX}{NODE}/attempts/2026-09-09.yaml": "schema: postmortem/v1\n"}),
        claim,
    )
    assert rejection is None
    assert bundle is not None
    assert bundle.size > 0
    assert len(bundle.digest) == 64
    assert bundle.proof_text == PROOF
    # The digest is content-addressed, not order-dependent.
    again, _ = bundles.validate(dict(reversed(list(bundle.files.items()))), claim)
    assert again is not None and again.digest == bundle.digest


def test_bundle_rejects_other_nodes_and_bad_shapes() -> None:
    claim = Claim(TARGET, NODE)
    for files, code in [
        ({f"{PREFIX}other/Proof.lean": PROOF}, "path-forbidden"),
        ({"../secrets": "x"}, "path-invalid"),
        ({f"/{PREFIX}{NODE}/Proof.lean": PROOF}, "path-invalid"),
        ({f"{PREFIX}{NODE}\\Proof.lean": PROOF}, "path-invalid"),
        ({}, "bundle-invalid"),
        ({f"{PREFIX}{NODE}/Proof.lean": 7}, "bundle-invalid"),
        ("not-an-object", "bundle-invalid"),
    ]:
        bundle, rejection = bundles.validate(files, claim)
        assert bundle is None, files
        assert rejection is not None and rejection.code == code, (files, rejection)


def test_waiver_allowed_only_when_the_proof_uses_native_decide() -> None:
    """F02-R8's rule, enforced here by the gate's own check rather than a copy of it."""
    claim = Claim(TARGET, NODE)
    waiver = {f"{PREFIX}{NODE}/waivers/native_decide.yaml": "schema: waiver/v1\n"}
    _, rejection = bundles.validate({**bundle_for(NODE), **waiver}, claim)
    assert rejection is not None and rejection.code == "path-forbidden"

    using = PROOF.replace("trivial", "by native_decide")
    ok, rejection = bundles.validate({f"{PREFIX}{NODE}/Proof.lean": using, **waiver}, claim)
    assert rejection is None and ok is not None


# --- the route (R2, R3) --------------------------------------------------------------------------


def test_tutorial_unauthenticated_only(harness: Harness) -> None:
    """AC4: a non-tutorial node needs a token; the tutorial node does not and gets a nonce."""
    refused = post(harness, {"node_id": NODE, "bundle": bundle_for(NODE)})
    assert refused.status_code == 401
    assert refused.json()["error"] == "unauthenticated"

    open_node = post(harness, {"node_id": TUTORIAL, "bundle": bundle_for(TUTORIAL)})
    assert open_node.status_code == 202, open_node.text
    doc = open_node.json()
    assert doc["state"] == "queued"
    assert doc["authenticated"] is False
    assert doc["nonce"]
    assert doc["public"] is True  # §7: the scratch repo is public and the caller is told

    token = harness.token_for("code_alice", "alice-p")
    with_token = post(harness, {"node_id": NODE, "bundle": bundle_for(NODE)}, token)
    assert with_token.status_code == 202, with_token.text
    assert with_token.json()["authenticated"] is True
    assert "nonce" not in with_token.json()


def test_proved_tutorial_node_is_still_precheckable(harness: Harness) -> None:
    """D-19 depends on it: the tutorial node is normally proved and off the frontier."""
    r = post(harness, {"node_id": PROVED_TUTORIAL, "bundle": bundle_for(PROVED_TUTORIAL)})
    assert r.status_code == 202, r.text
    assert r.json()["nonce"]


def test_unknown_node_is_404(harness: Harness) -> None:
    r = post(harness, {"node_id": "no-such-node", "bundle": bundle_for("no-such-node")})
    assert r.status_code == 404
    assert r.json()["error"] == "node-unknown"
    missing = post(harness, {"bundle": bundle_for()})
    assert missing.status_code == 400
    assert missing.json()["error"] == "node-id-missing"


def test_job_records_what_r3_requires(harness: Harness) -> None:
    r = post(harness, {"node_id": TUTORIAL, "bundle": bundle_for(TUTORIAL)})
    doc = r.json()
    job = precheck.load(harness.context, doc["id"])
    assert job is not None
    assert job.node_id == TUTORIAL
    assert job.target_id == TARGET
    assert len(job.statement_hash) == 64
    assert len(job.graph_commit) == 40
    assert len(job.bundle_digest) == 64
    assert job.created == "2026-09-09T12:00:00Z"
    assert job.state == "queued"
    assert job.anonymous and job.nonce and not job.nonce_consumed


def test_get_precheck_reports_the_job(harness: Harness) -> None:
    created = post(harness, {"node_id": TUTORIAL, "bundle": bundle_for(TUTORIAL)}).json()
    got = harness.client.get(f"/precheck/{created['id']}")
    assert got.status_code == 200
    doc = got.json()
    assert doc["id"] == created["id"]
    assert doc["state"] == "queued"
    assert "nonce" not in doc  # returned once, at creation, and never again (R2)
    assert harness.client.get("/precheck/NOPE").status_code == 404


def test_result_retention(harness: Harness) -> None:
    """AC9: a done job older than the window reports expired and serves no result body."""
    created = post(harness, {"node_id": TUTORIAL, "bundle": bundle_for(TUTORIAL)}).json()
    job = precheck.load(harness.context, created["id"])
    assert job is not None
    from dataclasses import replace  # noqa: PLC0415 — one use

    precheck.save(
        harness.context, replace(job, state="done", result={"verdict": "pass", "steps": []})
    )
    fresh = harness.client.get(f"/precheck/{created['id']}").json()
    assert fresh["state"] == "done"
    assert fresh["result"]["verdict"] == "pass"

    harness.clock.advance(days=precheck.RESULT_RETENTION_DAYS)
    old = harness.client.get(f"/precheck/{created['id']}").json()
    assert old["state"] == "expired"
    assert "result" not in old
    assert str(precheck.RESULT_RETENTION_DAYS) in old["message"]


# --- limits (R2, R8) -----------------------------------------------------------------------------


def test_anonymous_rate_limit() -> None:
    """AC5: the 21st anonymous tutorial precheck from one address in a day is 429."""
    h = make_harness({"OPN_API_ANONYMOUS_PRECHECKS_PER_DAY": "3"})
    headers = {"X-Forwarded-For": "203.0.113.9"}
    for n in range(3):
        r = h.client.post(
            "/precheck", json={"node_id": TUTORIAL, "bundle": bundle_for(TUTORIAL)}, headers=headers
        )
        assert r.status_code == 202, (n, r.text)
    over = h.client.post(
        "/precheck", json={"node_id": TUTORIAL, "bundle": bundle_for(TUTORIAL)}, headers=headers
    )
    assert over.status_code == 429
    assert int(over.headers["retry-after"]) > 0
    elsewhere = h.client.post(
        "/precheck",
        json={"node_id": TUTORIAL, "bundle": bundle_for(TUTORIAL)},
        headers={"X-Forwarded-For": "198.51.100.4"},
    )
    assert elsewhere.status_code == 202


def test_authenticated_precheck_limit() -> None:
    """R8: prechecks per identity per hour, published in the policy."""
    h = make_harness({"OPN_API_PRECHECKS_PER_HOUR": "2"})
    token = h.token_for("code_alice", "alice-p")
    for _ in range(2):
        assert post(h, {"node_id": NODE, "bundle": bundle_for(NODE)}, token).status_code == 202
    over = post(h, {"node_id": NODE, "bundle": bundle_for(NODE)}, token)
    assert over.status_code == 429
    assert h.client.get("/info.json").json()["rate_limit_policy"]["prechecks_per_hour"] == 2


@pytest.mark.parametrize("field", ["prechecks_per_hour", "anonymous_prechecks_per_address_per_day"])
def test_limits_are_published(harness: Harness, field: str) -> None:
    assert field in harness.client.get("/info.json").json()["rate_limit_policy"]


# --- T3: dispatch, poll, retrieve (R3, R5, R6, R10) ----------------------------------------------


@pytest.fixture(scope="module")
def key(tmp_path_factory: pytest.TempPathFactory) -> PrecheckKey:
    """The precheck keypair, made once: ssh-keygen is slow enough to be worth reusing."""
    return make_precheck_key(tmp_path_factory.mktemp("precheck-key"))


@pytest.fixture
def signed(harness: Harness, key: PrecheckKey) -> Harness:
    """A harness whose graph commits the precheck public key (C8 item 2)."""
    harness.commit_precheck_key(key.public)
    return harness


def start(h: Harness, node: str = TUTORIAL) -> dict[str, Any]:
    created = post(h, {"node_id": node, "bundle": bundle_for(node)})
    assert created.status_code == 202, created.text
    return dict(created.json())


def artifact_for(h: Harness, job_id: str, key: PrecheckKey | None, **overrides: Any) -> bytes:
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


def test_dispatch_recorded(harness: Harness) -> None:
    """AC3: a valid bundle becomes a branch push and a dispatch naming the job (R3)."""
    token = harness.token_for("code_alice", "alice-p")
    created = post(harness, {"node_id": NODE, "bundle": bundle_for(NODE)}, token).json()
    job_id = created["id"]

    (push,) = harness.githost.pushes
    assert push.repo == harness.settings.precheck_repo
    assert push.branch == f"job/{job_id}"
    assert push.base == harness.settings.precheck_branch
    # The branch carries the job record and the bundle under bundle/, at graph-relative paths,
    # which is what precheck.job applies to the checkout (R3, R4).
    assert set(push.files) == {"job.json", f"bundle/{PREFIX}{NODE}/Proof.lean"}
    record = __import__("json").loads(push.files["job.json"])
    assert record["id"] == job_id
    assert record["node_id"] == NODE
    assert record["graph_commit"] == created["graph_commit"]
    assert record["bundle_digest"] == created["bundle_digest"]

    (dispatch,) = harness.githost.dispatches
    assert dispatch.repo == harness.settings.precheck_repo
    assert dispatch.workflow == harness.settings.precheck_workflow
    assert dispatch.ref == f"job/{job_id}"
    assert dispatch.inputs == {"job_id": job_id}


def test_dispatch_failure_is_error(harness: Harness) -> None:
    """AC12, R10: dispatch raising is a 502 and a job marked error with the cause — never a
    silently dropped bundle (C7)."""
    harness.githost.app_failure = "POST /repos/x/git/refs returned 422: reference already exists"
    refused = post(harness, {"node_id": TUTORIAL, "bundle": bundle_for(TUTORIAL)})
    assert refused.status_code == 502
    assert refused.json()["error"] == "dispatch-failed"

    # The job exists and says why, so the submitter can find it by the id in the log (R10).
    ids = list(harness.store.jobs)
    assert len(ids) == 1
    job = precheck.load(harness.context, ids[0])
    assert job is not None
    assert job.state == "error"
    assert "reference already exists" in (job.error or "")


def test_poll_to_done(signed: Harness, key: PrecheckKey) -> None:
    """AC6: queued -> running while the run is in flight, then done with a verified result."""
    created = start(signed)
    job_id = created["id"]
    branch = f"job/{job_id}"

    assert signed.client.get(f"/precheck/{job_id}").json()["state"] == "queued"

    signed.githost.start_run(branch)
    running = signed.client.get(f"/precheck/{job_id}").json()
    assert running["state"] == "running"

    signed.githost.finish_run(
        branch, artifact=(f"result-{job_id}", artifact_for(signed, job_id, key))
    )
    done = signed.client.get(f"/precheck/{job_id}").json()
    assert done["state"] == "done", done
    assert done["result"]["verdict"] == "pass"
    assert done["result"]["attestation"]["signature"]["kind"] == "service"

    # Terminal is terminal: a later run state cannot change a stored verdict (R5).
    signed.githost.finish_run(branch, conclusion="failure")
    assert signed.client.get(f"/precheck/{job_id}").json()["state"] == "done"


def test_bad_signature_rejected(signed: Harness, key: PrecheckKey, tmp_path: Path) -> None:
    """AC7: a signature that does not verify against the committed key serves no attestation."""
    other = make_precheck_key(tmp_path, "other")
    for label, overrides in (
        ("another key", {"key": other}),
        ("unsigned", {"key": None}),
        ("tampered after signing", {"key": key, "tamper": True}),
    ):
        h = make_harness()
        h.commit_precheck_key(key.public)
        job_id = start(h)["id"]
        branch = f"job/{job_id}"
        h.githost.finish_run(
            branch, artifact=(f"result-{job_id}", artifact_for(h, job_id, **overrides))
        )
        doc = h.client.get(f"/precheck/{job_id}").json()
        assert doc["state"] == "error", (label, doc)
        assert "result" not in doc, label
        assert "signature" in doc["error"] or "signed" in doc["error"], (label, doc["error"])


def test_result_must_be_about_this_job(signed: Harness, key: PrecheckKey) -> None:
    """R6: a correctly signed result for another node or another graph commit is still refused."""
    for overrides in ({"node_id": "somewhere-else"}, {"graph_commit": "f" * 40}):
        h = make_harness()
        h.commit_precheck_key(key.public)
        job_id = start(h)["id"]
        h.githost.finish_run(
            f"job/{job_id}",
            artifact=(f"result-{job_id}", artifact_for(h, job_id, key, **overrides)),
        )
        doc = h.client.get(f"/precheck/{job_id}").json()
        assert doc["state"] == "error", (overrides, doc)


def test_run_failure_surfaced(signed: Harness) -> None:
    """AC8: a failed run is an error naming the conclusion and the run URL (C7)."""
    job_id = start(signed)["id"]
    run = signed.githost.finish_run(f"job/{job_id}", conclusion="failure")
    doc = signed.client.get(f"/precheck/{job_id}").json()
    assert doc["state"] == "error"
    assert "failure" in doc["error"]
    assert doc["run_url"] == run.url


def test_successful_run_without_an_artifact_is_an_error(signed: Harness) -> None:
    """R5: `if-no-files-found: warn` means a green run can still carry no result."""
    job_id = start(signed)["id"]
    signed.githost.finish_run(f"job/{job_id}")
    doc = signed.client.get(f"/precheck/{job_id}").json()
    assert doc["state"] == "error"
    assert "no result" in doc["error"]


def test_lookup_failure_leaves_the_job_alone(signed: Harness) -> None:
    """C7: GitHub being unreachable is an outage, not a verdict — the job stays where it was."""
    job_id = start(signed)["id"]
    signed.githost.lookup_failure = "GET /actions/workflows/precheck.yml/runs failed: ConnectError"
    doc = signed.client.get(f"/precheck/{job_id}").json()
    assert doc["state"] == "queued"

    signed.githost.lookup_failure = None
    signed.githost.start_run(f"job/{job_id}")
    assert signed.client.get(f"/precheck/{job_id}").json()["state"] == "running"


def test_polling_a_running_job_does_not_rewrite_it(signed: Harness) -> None:
    """Q3 polls on read, so a caller watching a job asks every few seconds; only a change is
    written. Checked by counting the store's writes, not by reading the code."""
    job_id = start(signed)["id"]
    signed.githost.start_run(f"job/{job_id}")
    writes = 0
    original = signed.store.put_job

    def counted(*args: Any, **kwargs: Any) -> None:
        nonlocal writes
        writes += 1
        original(*args, **kwargs)

    signed.store.put_job = counted  # type: ignore[method-assign]
    for _ in range(4):
        assert signed.client.get(f"/precheck/{job_id}").json()["state"] == "running"
    assert writes == 1, "only the queued -> running transition should have been written"


def test_an_unreadable_key_does_not_burn_the_job(harness: Harness, key: PrecheckKey) -> None:
    """C7: if the graph cannot be read, the committed key is unknown and the result cannot be
    verified — so say so and leave the job alone. An outage must not become a failed precheck."""
    harness.commit_precheck_key(key.public)
    job_id = start(harness)["id"]
    harness.githost.finish_run(
        f"job/{job_id}", artifact=(f"result-{job_id}", artifact_for(harness, job_id, key))
    )
    del harness.githost.files["keys/precheck.pub"]
    harness.context.files.pop("keys/precheck.pub", None)

    refused = harness.client.get(f"/precheck/{job_id}")
    assert refused.status_code == 503
    assert refused.json()["error"] == "graph-unreachable"
    job = precheck.load(harness.context, job_id)
    assert job is not None and job.state == "queued", "the job must not have been marked error"

    # The key comes back, and the same poll now completes the job.
    harness.commit_precheck_key(key.public)
    assert harness.client.get(f"/precheck/{job_id}").json()["state"] == "done"


def test_expired_job_is_not_polled(signed: Harness, key: PrecheckKey) -> None:
    """AC9 with T3: past the window the job is expired and the host is not called again."""
    job_id = start(signed)["id"]
    signed.githost.finish_run(
        f"job/{job_id}", artifact=(f"result-{job_id}", artifact_for(signed, job_id, key))
    )
    assert signed.client.get(f"/precheck/{job_id}").json()["state"] == "done"
    signed.clock.advance(days=precheck.RESULT_RETENTION_DAYS)
    assert signed.client.get(f"/precheck/{job_id}").json()["state"] == "expired"
