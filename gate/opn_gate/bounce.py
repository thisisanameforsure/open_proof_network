"""The precheck-attestation bounce rule (D-4; F00-R13, Q1).

The authoritative gate requires an attached passing precheck attestation. It is attached as a
fenced ``json`` block in the pull-request body whose first line is ``opn-precheck-attestation``;
the gate parses the first such block. The PR body is not evidentiary: the authoritative
attestation records only the hash and signature kind of what it consumed. The bounce rule keeps
garbage out of CI and proves nothing else — every verdict is re-derived — so no signature is
verified here.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from opn_gate import schemas

ACCEPTED_SCHEMAS: tuple[str, ...] = ("attestation/v1", "attestation/v2")

MARKER = "opn-precheck-attestation"
_BLOCK_RE = re.compile(r"```json[ \t]*\r?\n" + MARKER + r"[ \t]*\r?\n(?P<body>.*?)\r?\n```", re.S)
TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


@dataclass(frozen=True)
class PrecheckPolicy:
    """What the bounce rule needs: the PR body, the graph's rules, and what was claimed."""

    pr_body: str
    accepted_signatures: tuple[str, ...]
    max_age_s: int
    now: datetime
    node_id: str
    statement_hash: str


@dataclass(frozen=True)
class Decision:
    bounced: bool
    reason: str | None = None
    attestation_hash: str | None = None
    signature_kind: str | None = None
    details: dict[str, Any] = field(default_factory=dict)


def extract_block(pr_body: str) -> str | None:
    m = _BLOCK_RE.search(pr_body or "")
    return m.group("body") if m else None


def render_block(attestation: dict[str, Any]) -> str:
    """The inverse of ``extract_block``: what a submitter pastes into the PR body."""
    return f"```json\n{MARKER}\n{json.dumps(attestation, sort_keys=True, indent=2)}\n```"


def parse_timestamp(value: str) -> datetime:
    return datetime.strptime(value, TIMESTAMP_FORMAT).replace(tzinfo=UTC)


def evaluate(policy: PrecheckPolicy) -> Decision:  # noqa: PLR0911 — one return per rule
    body = extract_block(policy.pr_body)
    if body is None:
        return Decision(True, "no precheck attestation attached to the pull request")
    raw = body.encode("utf-8")
    digest = schemas.content_hash(raw)
    try:
        doc = json.loads(body)
    except json.JSONDecodeError as exc:
        return Decision(True, f"precheck attestation is not valid JSON: {exc.msg}", digest)
    schema_id = doc.get("schema") if isinstance(doc, dict) else None
    if schema_id not in ACCEPTED_SCHEMAS:
        return Decision(True, f"precheck attestation schema {schema_id!r} is not accepted", digest)
    problems = schemas.violations(doc, str(schema_id))
    if problems:
        return Decision(
            True,
            f"precheck attestation does not validate against {schema_id}",
            digest,
            details={"violations": [f"{v.path}: {v.message}" for v in problems[:5]]},
        )
    kind = str(doc["signature"]["kind"])
    if kind not in policy.accepted_signatures:
        return Decision(
            True,
            f"precheck signature kind {kind!r} is not accepted by this graph",
            digest,
            kind,
            {"accepted": list(policy.accepted_signatures)},
        )
    if doc["verdict"] != "pass":
        return Decision(True, f"precheck attestation verdict is {doc['verdict']!r}", digest, kind)
    if doc["node_id"] != policy.node_id or doc["statement_hash"] != policy.statement_hash:
        return Decision(
            True, "precheck attestation is for a different node or statement", digest, kind
        )
    age = (policy.now - parse_timestamp(doc["signature"]["timestamp"])).total_seconds()
    if age > policy.max_age_s or age < 0:
        return Decision(
            True,
            f"precheck attestation is {age:.0f}s old; max accepted age is {policy.max_age_s}s",
            digest,
            kind,
        )
    return Decision(False, None, digest, kind)
