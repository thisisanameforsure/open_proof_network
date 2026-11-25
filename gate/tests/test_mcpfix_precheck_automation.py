"""mcpfix (testers 2026-11-25, t257 item 4 and t257b item 6): a precheck's signed attestation
records the automation the agent declared on the job.

The service keeps ``automation`` on the job (F25-R3) and the result document echoes it at the
top level, but the attestation inside was built with no submission block, so it said
``automation: null`` and ``model_and_tooling: undeclared`` for every precheck."""

from __future__ import annotations

from pathlib import Path

from harness import make_context
from precheck import job as precheck_job

from opn_gate import pipeline, schemas

AUTOMATION = {
    "method": "agent",
    "models": ["claude-opus-5-5"],
    "framework": "claude-code",
}


def _job(automation: object) -> dict[str, object]:
    return {"graph_commit": "1" * 40, "automation": automation}


def test_the_attestation_records_the_declared_automation(tmp_path: Path) -> None:
    ctx = make_context(tmp_path)
    verdict = pipeline.run_steps(ctx)
    doc = precheck_job.attest(ctx, verdict, _job(dict(AUTOMATION)))
    assert doc["automation"] == AUTOMATION
    assert schemas.violations(doc) == []


def test_no_declaration_stays_null(tmp_path: Path) -> None:
    """A job without automation (the anonymous tutorial precheck) attests as before."""
    ctx = make_context(tmp_path)
    verdict = pipeline.run_steps(ctx)
    for absent in (None, "not-an-object"):
        doc = precheck_job.attest(ctx, verdict, _job(absent))
        assert doc["automation"] is None
        assert doc["model_and_tooling"] == "undeclared"
