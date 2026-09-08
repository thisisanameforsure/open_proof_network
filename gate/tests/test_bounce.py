"""F00-T5: the precheck-attestation bounce rule (R13; AC18, AC19)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import samples
from fakes import FakeToolchain
from harness import make_context

from opn_gate import attestation, bounce, pipeline, schemas
from opn_gate.bounce import PrecheckPolicy

NOW = datetime(2026, 9, 8, 12, 0, 0, tzinfo=UTC)


def precheck_doc(ctx: Any, **overrides: Any) -> dict[str, Any]:
    """A passing precheck attestation for the fixture tutorial node, sealed one hour ago."""
    verdict = pipeline.run_steps(ctx)
    doc = attestation.build(ctx, verdict, graph_commit=None, clock=lambda: NOW - timedelta(hours=1))
    doc.update(overrides)
    return doc


def policy(
    ctx: Any, body: str, accepted: tuple[str, ...] = ("service", "contributor", "none")
) -> PrecheckPolicy:
    assert ctx.node is not None
    return PrecheckPolicy(
        pr_body=body,
        accepted_signatures=accepted,
        max_age_s=int(ctx.spec["precheck_max_age_s"]),
        now=NOW,
        node_id=ctx.claim.node_id,
        statement_hash=ctx.node.statement.statement_hash,
    )


def test_no_precheck_bounces(tmp_path: Path) -> None:
    """AC18: no attestation → verdict bounced, no step ran."""
    ctx = make_context(tmp_path)
    pipeline.run_steps(ctx)  # loads the node for the policy
    fake = FakeToolchain()
    ctx.toolchain = fake
    ctx.data.clear()
    verdict = pipeline.run_submission(ctx, precheck=policy(ctx, "Fixes #1\n\nno block here"))
    assert verdict.verdict == "bounced"
    assert verdict.steps == ()
    assert fake.calls == []
    assert (
        verdict.diagnostic is not None and "no precheck attestation" in verdict.diagnostic.message
    )
    assert verdict.data["precheck_attestation"] == {"hash": None, "signature_kind": None}


def test_signature_kind_policy(tmp_path: Path) -> None:
    """AC19: unsigned accepted when the spec lists none; bounced when only service is accepted."""
    ctx = make_context(tmp_path)
    doc = precheck_doc(ctx)
    body = "PR text\n\n" + bounce.render_block(doc) + "\n\nmore text"

    ctx.data.clear()
    verdict = pipeline.run_submission(ctx, precheck=policy(ctx, body, ("none",)))
    assert verdict.verdict == "pass"
    consumed = verdict.data["precheck_attestation"]
    assert consumed["signature_kind"] == "none"
    block = bounce.extract_block(body)
    assert block is not None
    assert consumed["hash"] == schemas.content_hash(block.encode())

    ctx.data.clear()
    verdict = pipeline.run_submission(ctx, precheck=policy(ctx, body, ("service",)))
    assert verdict.verdict == "bounced"
    assert verdict.steps == ()
    assert verdict.diagnostic is not None and "'none' is not accepted" in verdict.diagnostic.message


def test_bounce_reasons(tmp_path: Path) -> None:
    ctx = make_context(tmp_path)
    good = precheck_doc(ctx)

    stale = dict(good)
    stale["signature"] = dict(good["signature"], timestamp="2026-09-01T00:00:00Z")
    d = bounce.evaluate(policy(ctx, bounce.render_block(stale)))
    assert d.bounced and "old" in (d.reason or "")

    failed = dict(good, verdict="fail", first_failing_step=5)
    d = bounce.evaluate(policy(ctx, bounce.render_block(failed)))
    assert d.bounced and "verdict is 'fail'" in (d.reason or "")

    other = dict(good, node_id="and-reassoc")
    d = bounce.evaluate(policy(ctx, bounce.render_block(other)))
    assert d.bounced and "different node" in (d.reason or "")

    d = bounce.evaluate(policy(ctx, "```json\nopn-precheck-attestation\n{not json\n```"))
    assert d.bounced and "not valid JSON" in (d.reason or "")

    invalid = samples.attestation(runner="cloud")
    d = bounce.evaluate(policy(ctx, bounce.render_block(invalid)))
    assert d.bounced and "does not validate" in (d.reason or "")
    assert d.details["violations"]

    d = bounce.evaluate(policy(ctx, bounce.render_block(good)))
    assert not d.bounced and d.signature_kind == "none" and d.attestation_hash


def test_first_marked_block_wins() -> None:
    body = '```json\n{"decoy": true}\n```\n```json\nopn-precheck-attestation\n{"a": 1}\n```\n'
    assert bounce.extract_block(body) == '{"a": 1}'
    assert bounce.extract_block("```json\r\nopn-precheck-attestation\r\n{}\r\n```") == "{}"
    assert bounce.extract_block("") is None
