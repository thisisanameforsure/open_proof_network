# ruff: noqa: F811 — the imported key fixture is the parameter its test names
"""mcpfix (lead; verifier VC, item 8, 2026-11-25): a write the host refused with a 5xx says that
nothing opened and that a retry is safe, and when to retry.

VC's gloss failed three times and its proof twice with ``502 pull-request-failed`` ("…returned
500"), and a precheck once with ``502 dispatch-failed``; none said whether anything was half
made or whether to retry, so VC listed its own submissions to find out. A host refusal of this
kind leaves no pull request and no live job, and the same call opens once the host answers."""

from __future__ import annotations

from api_fakes import Harness, PrecheckKey
from test_precheck import TUTORIAL, bundle_for, post
from test_rejections_submissions import key, submit  # noqa: F401 — the key fixture


def says_retry(body: dict[str, object]) -> None:
    message = str(body["message"]).lower()
    assert "retry" in message and "nothing" in message, message
    details = body.get("details")
    assert isinstance(details, dict) and isinstance(details.get("retry_after_s"), int), body


def test_a_pull_request_the_host_refused_says_retry(harness: Harness, key: PrecheckKey) -> None:
    token = harness.token_for("code_alice", "alice")
    job = harness.tutorial_job(key, token=token)
    harness.client.get(f"/precheck/{job['id']}")
    harness.githost.app_failure = "POST /repos/g/pulls returned 500"
    r = submit(harness, token, precheck_job_id=job["id"])
    assert (r.status_code, r.json()["error"]) == (502, "pull-request-failed")
    says_retry(r.json())


def test_a_dispatch_the_host_refused_says_retry(harness: Harness) -> None:
    harness.githost.app_failure = (
        "POST /repos/x/actions/workflows/precheck.yml/dispatches returned 500"
    )
    r = post(harness, {"node_id": TUTORIAL, "bundle": bundle_for(TUTORIAL)})
    assert (r.status_code, r.json()["error"]) == (502, "dispatch-failed")
    says_retry(r.json())
