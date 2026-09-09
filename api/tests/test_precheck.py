"""F06-T1: bundles, jobs and the two routes (R1, R2, R3, R8; AC1, AC2, AC4, AC5, AC9)."""

from __future__ import annotations

from typing import Any

import pytest
from api_fakes import Harness, make_harness

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
