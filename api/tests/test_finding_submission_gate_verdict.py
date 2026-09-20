"""Finding submission-gate-verdict (agents D and E, graph PRs #123 and #124): when the gate
refuses a pull request the service says ``waiting_on: gate-failed`` and nothing about *why*. The
reason sits in the run's log on GitHub, which an HTTP or MCP contributor with no GitHub login
cannot read; agent E's proposal was refused ``hazard-unacknowledged`` on ``100 ≤ p`` and it could
only poll a red check. The gate run already keeps its verdict as an artifact
(``gate-<pr>-<attempt>``), and the service already reads artifacts for prechecks.

F07-T26: a pull request whose gate failed carries ``gate_verdict`` — the verdict, where it first
failed and the gate's own diagnostic — read once per head commit.
"""

from __future__ import annotations

import io
import json
import zipfile
from typing import Any

from api_fakes import Harness
from test_pending_submissions import record

from opn_api.mcp import results

RUN_ID = 35498775944
RUN_URL = f"https://github.com/o/r/actions/runs/{RUN_ID}"
ADMISSION = {
    "verdict": "fail",
    "first_failing_check": "hazards",
    "diagnostic": {
        "code": "hazard-unacknowledged",
        "message": "1 unacknowledged hazard finding(s); first: off-by-one-range at 100 ≤ p",
        "details": {
            "findings": [{"checker": "off-by-one-range", "location": "100 ≤ p", "message": "m"}]
        },
    },
    "checks": [{"check": "layout", "result": "pass"}],
}


def zipped(**files: dict[str, Any]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, doc in files.items():
            archive.writestr(name, json.dumps(doc))
    return buffer.getvalue()


def failed_gate(h: Harness, number: int = 7, *, artifact: bytes | None = None) -> None:
    h.store.put_submission(record(number, kind="variant", node_id="variant-0badc0de"))
    h.githost.set_pull_request_state(
        number,
        mergeable_state="blocked",
        head_sha="f" * 40,
        runs=[
            {
                "name": "gate",
                "status": "completed",
                "conclusion": "failure",
                "url": RUN_URL,
                "jobs": [{"name": "gate (x)", "status": "completed", "conclusion": "failure"}],
            }
        ],
    )
    if artifact is not None:
        h.githost.artifacts[(RUN_ID, f"gate-{number}-1")] = zipped(**{"old.json": {"x": 1}})
        h.githost.artifacts[(RUN_ID, f"gate-{number}-2")] = artifact  # the later attempt counts


def get(h: Harness, number: int = 7) -> dict[str, Any]:
    r = h.client.get(f"/submissions/{number}")
    assert r.status_code == 200, r.text
    doc: dict[str, Any] = r.json()
    return doc


def test_a_failed_gate_says_why(harness: Harness) -> None:
    failed_gate(harness, artifact=zipped(**{"admission.json": ADMISSION}))
    doc = get(harness)
    assert doc["pull_request"]["waiting_on"] == "gate-failed"
    assert doc["gate_verdict"] == {
        "verdict": "fail",
        "first_failing": "hazards",
        "diagnostic": ADMISSION["diagnostic"],
    }
    assert results.violations("get_submission", doc) == []


def test_a_proofs_verdict_names_its_step(harness: Harness) -> None:
    verdict: dict[str, Any] = {
        "verdict": "fail",
        "first_failing_step": 4,
        "diagnostic": {"code": "memory-exceeded", "message": "killed", "details": {}},
    }
    failed_gate(harness, artifact=zipped(**{"verdict.json": verdict, "attestation.json": {"a": 1}}))
    assert get(harness)["gate_verdict"]["first_failing"] == 4


def test_it_is_read_once_per_head_commit(harness: Harness) -> None:
    failed_gate(harness, artifact=zipped(**{"admission.json": ADMISSION}))
    get(harness)
    calls = harness.githost.artifact_reads
    get(harness)
    get(harness)
    assert harness.githost.artifact_reads == calls == 1


def test_no_artifact_or_a_host_failure_is_null_never_a_500(harness: Harness) -> None:
    failed_gate(harness)  # the run kept nothing (it failed before the gate ran)
    assert get(harness)["gate_verdict"] is None
    harness.githost.artifact_failure = "boom"
    harness.context.verdicts.clear()
    assert get(harness)["gate_verdict"] is None


def test_a_pull_request_that_did_not_fail_reads_no_artifact(harness: Harness) -> None:
    harness.store.put_submission(record(8, kind="annex"))
    harness.githost.set_pull_request_state(
        8, runs=[{"name": "gate", "status": "completed", "conclusion": "success", "url": RUN_URL}]
    )
    assert get(harness, 8)["gate_verdict"] is None
    assert harness.githost.artifact_reads == 0
