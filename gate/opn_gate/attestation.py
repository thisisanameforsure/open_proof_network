"""Build the attestation record from a verdict (F00-R8; D-5, D-34; attestation/v1).

Everything outside ``runner``, ``merge_commit`` and ``signature`` must be a function of the
checked tree and the pinned tooling alone, so that two runs anywhere agree byte for byte once
those three are masked (D-5). ``compare`` is that comparison.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from opn_gate import schemas
from opn_gate.bounce import TIMESTAMP_FORMAT
from opn_gate.pipeline import Verdict
from opn_gate.steps.base import RunContext
from opn_gate.toolchain import ResolvedToolchain

SCHEMA = "attestation/v3"  # v3 (F02-R9): trust_base
ACCEPTED_SCHEMAS: tuple[str, ...] = ("attestation/v1", "attestation/v2", "attestation/v3")
MASKED_FIELDS: tuple[str, ...] = ("runner", "merge_commit", "signature")
TRUST_KERNEL = "kernel"
TRUST_COMPILER = "compiler"
Clock = Callable[[], datetime]


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


def build(
    ctx: RunContext,
    verdict: Verdict,
    *,
    graph_commit: str | None,
    tooling: dict[str, str | None] | None = None,
    clock: Clock = utc_now,
) -> dict[str, Any]:
    """The attestation for ``verdict``; validated against attestation/v1 before it is returned."""
    tc: ResolvedToolchain | None = verdict.data.get("toolchain")
    node = ctx.node
    max_bytes = ctx.settings.diagnostic_max_bytes
    verdict_doc = verdict.as_dict(max_bytes)
    statement_hash = node.statement.statement_hash if node else _statement_hash_fallback(ctx)
    artifact_hash = None
    if node is not None and node.proof_path.is_file():
        artifact_hash = schemas.content_hash(node.proof_path.read_bytes())
    precheck = verdict.data.get("precheck_attestation") or {"hash": None, "signature_kind": None}
    doc: dict[str, Any] = {
        "schema": SCHEMA,
        "graph_id": ctx.spec["graph_id"],
        "node_id": ctx.claim.node_id,
        "statement_hash": statement_hash,
        "lean_toolchain": ctx.spec["lean_toolchain"],
        "toolchain_hash": tc.toolchain_hash if tc else None,
        "mathlib_sha": ctx.spec["mathlib_sha"],
        "gate_spec_hash": ctx.gate_spec_hash,
        "network_commit": ctx.spec["network_commit"],
        "graph_commit": graph_commit,
        "runner": ctx.settings.runner,
        "tooling": {
            "model": (tooling or {}).get("model"),
            "harness": (tooling or {}).get("harness"),
        },
        "verdict": verdict_doc["verdict"],
        "first_failing_step": verdict_doc["first_failing_step"],
        "diagnostic": verdict_doc["diagnostic"],
        "steps": verdict_doc["steps"],
        "artifact_hash": artifact_hash,
        "precheck_attestation": {
            "hash": precheck.get("hash"),
            "signature_kind": precheck.get("signature_kind"),
        },
        "merge_commit": None,
        "review": None,
        # F02-R9: a function of the checked tree (the waiver step 5 accepted), never of the run.
        "trust_base": TRUST_COMPILER if verdict.data.get("waiver") else TRUST_KERNEL,
        "signature": {
            "kind": "none",
            "key_id": None,
            "value": None,
            "timestamp": clock().astimezone(UTC).strftime(TIMESTAMP_FORMAT),
        },
    }
    return schemas.validate(doc, SCHEMA)


def _statement_hash_fallback(ctx: RunContext) -> str:
    """When step 2 never loaded the node, hash Statement.lean directly if it exists."""
    path = ctx.graph_root / "targets" / ctx.claim.target_id / "nodes" / ctx.claim.node_id
    statement = path / "Statement.lean"
    if statement.is_file():
        return schemas.content_hash(statement.read_bytes())
    return "0" * 64


STEP9_FIELDS: tuple[str, ...] = ("review", "reviewer")  # v2 block; v1 string


def with_step9(reproduction: dict[str, Any], committed: dict[str, Any]) -> dict[str, Any]:
    """A reproduction replays steps 1-8 (D-5); step 9's record is copied from the committed one."""
    out = dict(reproduction)
    for key in STEP9_FIELDS:
        if key in committed:
            out[key] = committed[key]
    return out


def masked(doc: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in doc.items() if k not in MASKED_FIELDS}


def compare(a: dict[str, Any], b: dict[str, Any]) -> list[str]:
    """D-5: the fields that differ once the run-environment fields are masked."""
    ma, mb = masked(a), masked(b)
    return sorted(k for k in set(ma) | set(mb) if ma.get(k) != mb.get(k))


def signed_bytes(doc: dict[str, Any]) -> bytes:
    """What a signature covers: the canonical JSON of the record without its signature block."""
    unsigned = {k: v for k, v in doc.items() if k != "signature"}
    return schemas.canonical_json(unsigned)
