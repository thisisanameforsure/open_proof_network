"""F22-T24 (feature request A): the gate's warnings reach a writer through
``GET /submissions/<id>``.

On 2026-10-06 four writers learned of ``explainer-name-unanchored`` only from the Actions log, and
``gate_verdict`` stayed null on every green pull request because it explains refusals only. The
gate job now keeps its classification as ``classify-<pr>-<attempt>`` for every pull request it
classified (the graph's ``gate.yml``); the service reads it once per head commit, for a green
pull request as for a red one, and answers it as ``gate_report``: whether the classification
passed, its warnings and its problems, in the gate's own words.
"""

from __future__ import annotations

from typing import Any

from api_fakes import Harness
from test_finding_submission_gate_verdict import RUN_ID, RUN_URL, get, zipped
from test_pending_submissions import record

from opn_api.mcp import results

WARNING = {
    "code": "explainer-name-unanchored",
    "message": "the section 'Idea' cites `Finset.prod`, which none of the constants its steps use",
    "details": {},
}
CLASSIFICATION = {"mode": "explainer", "ok": True, "problems": [], "warnings": [WARNING]}


def green_words(h: Harness, number: int = 7, *, artifact: bytes | None = None) -> None:
    h.store.put_submission(record(number, kind="explainer", node_id="n"))
    h.githost.set_pull_request_state(
        number,
        mergeable_state="clean",
        head_sha="e" * 40,
        runs=[
            {
                "name": "gate",
                "status": "completed",
                "conclusion": "success",
                "url": RUN_URL,
                "jobs": [{"name": "gate (x)", "status": "completed", "conclusion": "success"}],
            }
        ],
    )
    if artifact is not None:
        h.githost.artifacts[(RUN_ID, f"classify-{number}-1")] = artifact


def test_a_green_words_pull_request_shows_its_warnings(harness: Harness) -> None:
    green_words(harness, artifact=zipped(**{"classification.json": CLASSIFICATION}))
    doc = get(harness)
    assert doc["gate_verdict"] is None  # a refusal's reason, and there is none
    assert doc["gate_report"] == {"ok": True, "warnings": [WARNING], "problems": []}
    assert results.violations("get_submission", doc) == []


def test_it_is_read_once_per_head_commit(harness: Harness) -> None:
    green_words(harness, artifact=zipped(**{"classification.json": CLASSIFICATION}))
    get(harness)
    calls = harness.githost.artifact_reads
    get(harness)
    assert harness.githost.artifact_reads == calls


def test_no_classification_is_null(harness: Harness) -> None:
    green_words(harness)  # a run on the pinned gate before F22-T24 keeps none
    doc: dict[str, Any] = get(harness)
    assert doc["gate_report"] is None
