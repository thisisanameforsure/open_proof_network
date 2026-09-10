"""F00-T5: the attestation builder (R8; AC17) and the D-5 comparison."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import samples
from fakes import FakeToolchain
from harness import make_context, node_dir

from opn_gate import attestation, bounce, pipeline, schemas, submission
from opn_gate.toolchain import AxiomResult, ReplayResult

FIXED = datetime(2026, 9, 8, 3, 4, 5, tzinfo=UTC)
R8_FIELDS = (
    "graph_id",
    "gate_spec_hash",
    "network_commit",
    "runner",
    "precheck_attestation",
    "merge_commit",
    "signature",
    "review",
)
D34_FIELDS = (
    "schema",
    "statement_hash",
    "node_id",
    "mathlib_sha",
    "toolchain_hash",
    "tooling",
    "verdict",
    "first_failing_step",
    "diagnostic",
    "artifact_hash",
)


def test_attestation_fields_and_schema(tmp_path: Path) -> None:
    """AC17."""
    ctx = make_context(tmp_path)
    verdict = pipeline.run_steps(ctx)
    doc = attestation.build(ctx, verdict, graph_commit="1" * 40, clock=lambda: FIXED)
    assert schemas.violations(doc) == []
    for field in R8_FIELDS + D34_FIELDS:
        assert field in doc, field
    assert doc["verdict"] == "pass"
    assert doc["runner"] == "local"
    assert doc["graph_id"] == "propositional"
    assert doc["node_id"] == "tutorial-and-swap"
    assert doc["lean_toolchain"] == "leanprover/lean4:v4.33.1"
    assert doc["toolchain_hash"] == verdict.data["toolchain"].toolchain_hash
    assert doc["gate_spec_hash"] == ctx.gate_spec_hash
    assert doc["graph_commit"] == "1" * 40
    assert doc["statement_hash"] == ctx.node.statement.statement_hash if ctx.node else False
    assert doc["artifact_hash"] == schemas.content_hash((node_dir(ctx) / "Proof.lean").read_bytes())
    assert doc["signature"] == {
        "kind": "none",
        "key_id": None,
        "value": None,
        "timestamp": "2026-09-08T03:04:05Z",
    }
    assert [s["result"] for s in doc["steps"]] == ["pass"] * 7
    assert doc["merge_commit"] is None and doc["review"] is None
    assert doc["schema"] == "attestation/v4"
    assert doc["trust_base"] == "kernel"  # F02-R9: no waiver, the kernel checked everything


def test_failed_run_still_attests(tmp_path: Path) -> None:
    fake = FakeToolchain(axiom_result=AxiomResult(ok=True, axioms=frozenset({"sorryAx"})))
    ctx = make_context(tmp_path, toolchain=fake)
    verdict = pipeline.run_steps(ctx)
    doc = attestation.build(ctx, verdict, graph_commit=None, clock=lambda: FIXED)
    assert schemas.violations(doc) == []
    assert doc["verdict"] == "fail"
    assert doc["first_failing_step"] == 5
    assert doc["diagnostic"]["code"] == "axiom-not-allowed"
    assert doc["artifact_hash"] is not None  # D-34: the artifact is recorded on fail too


def test_step1_failure_attests_without_toolchain_hash(tmp_path: Path) -> None:
    ctx = make_context(tmp_path, toolchain=FakeToolchain(missing=True))
    verdict = pipeline.run_steps(ctx)
    doc = attestation.build(ctx, verdict, graph_commit=None, clock=lambda: FIXED)
    assert schemas.violations(doc) == []
    assert doc["toolchain_hash"] is None
    assert doc["statement_hash"] == ctx.node.statement.statement_hash if ctx.node else True


def test_tooling_is_recorded_as_declared(tmp_path: Path) -> None:
    ctx = make_context(tmp_path)
    verdict = pipeline.run_steps(ctx)
    doc = attestation.build(
        ctx,
        verdict,
        graph_commit=None,
        tooling={"model": "claude-fable-5-1", "harness": "claude-code"},
        clock=lambda: FIXED,
    )
    assert doc["tooling"] == {"model": "claude-fable-5-1", "harness": "claude-code"}


def test_compare_masks_only_the_three_run_fields(tmp_path: Path) -> None:
    ctx = make_context(tmp_path)
    verdict = pipeline.run_steps(ctx)
    a = attestation.build(ctx, verdict, graph_commit=None, clock=lambda: FIXED)
    later = datetime(2026, 9, 9, tzinfo=UTC)
    b = attestation.build(ctx, verdict, graph_commit=None, clock=lambda: later)
    b["runner"] = "hosted"
    b["merge_commit"] = "2" * 40
    b["signature"] = {
        "kind": "gate",
        "key_id": "k",
        "value": "sig",
        "timestamp": "2026-09-09T00:00:00Z",
    }
    assert attestation.compare(a, b) == []
    b["artifact_hash"] = "0" * 64
    assert attestation.compare(a, b) == ["artifact_hash"]


def test_signed_bytes_exclude_signature_and_are_canonical(tmp_path: Path) -> None:
    ctx = make_context(tmp_path)
    doc = attestation.build(ctx, pipeline.run_steps(ctx), graph_commit=None, clock=lambda: FIXED)
    payload = attestation.signed_bytes(doc)
    assert b'"signature"' not in payload
    assert payload == schemas.canonical_json({k: v for k, v in doc.items() if k != "signature"})


def test_attestation_stays_under_budget_with_huge_diagnostic(tmp_path: Path) -> None:
    fake = FakeToolchain(replay=ReplayResult(ok=False, output="y" * 200_000))
    ctx = make_context(tmp_path, toolchain=fake)
    doc = attestation.build(ctx, pipeline.run_steps(ctx), graph_commit=None, clock=lambda: FIXED)
    assert len(schemas.canonical_json(doc)) < 64 * 1024
    assert doc["diagnostic"]["truncated"] is True


# --- F07-T5 / AC18: who submitted, and what they said drove it (R13; D-23, D-34) -----------------


def test_undeclared_tooling(tmp_path: Path) -> None:
    """AC18: a hand-opened pull request has no opn-submission block, so the record says
    `undeclared` rather than inventing a model, and carries no pseudonym."""
    ctx = make_context(tmp_path)
    verdict = pipeline.run_steps(ctx)
    doc = attestation.build(ctx, verdict, graph_commit="1" * 40)
    assert doc["model_and_tooling"] == submission.UNDECLARED
    assert doc["submitter"] is None
    assert schemas.violations(doc, attestation.SCHEMA) == []


def test_submission_block_is_carried_into_the_record(tmp_path: Path) -> None:
    """R13: the block's pseudonym and declared tooling reach the attestation verbatim.

    Declared, never verified — D-1 keeps the gate blind to tooling — and recorded because the
    corpus is only labelled if this field is there (D-34).
    """
    ctx = make_context(tmp_path)
    verdict = pipeline.run_steps(ctx)
    block = samples.submission_meta(
        identity={"pseudonym": "alice", "proof_kind": "tutorial"},
        tooling={"model": "claude-opus-5", "version": "2026-09", "harness": "claude-code"},
    )
    doc = attestation.build(ctx, verdict, graph_commit="1" * 40, submission=block)
    assert doc["submitter"] == "alice"
    assert doc["model_and_tooling"] == "claude-opus-5 2026-09 claude-code"
    assert schemas.violations(doc, attestation.SCHEMA) == []


def test_a_malformed_block_is_the_same_as_none(tmp_path: Path) -> None:
    """C7: the block is a declaration the gate never checks, so a broken one must not fail a
    proof — it is recorded as undeclared, like a hand-opened pull request."""
    body = "```json\nopn-submission\n{not json at all}\n```"
    assert submission.extract(body) is None
    invalid = samples.submission_meta(artifact_type="sketch")
    assert submission.extract(submission.render_block(invalid)) is None
    assert submission.model_and_tooling(None) == submission.UNDECLARED


def test_the_block_round_trips_through_a_pull_request_body() -> None:
    """R2: what the service writes is what the gate reads, past the other block in the body."""
    meta = samples.submission_meta()
    body = (
        "Submitted through the service.\n\n"
        + bounce.render_block(samples.attestation())
        + "\n\n"
        + submission.render_block(meta)
    )
    assert submission.extract(body) == meta
    assert bounce.extract_block(body) is not None  # the precheck block is still found
