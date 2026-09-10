"""The ``opn-submission`` block in a pull-request body (F07-R2, R13; ``submission-meta/v1``).

Beside the ``opn-precheck-attestation`` block the bounce rule reads (``opn_gate.bounce``), a
service-opened pull request carries one more fenced JSON block declaring who submitted, which of
D-12's five artifacts it is, and the model and tooling D-23 wants disclosed. The service writes
it; the authoritative gate copies it into the attestation.

The block is a *declaration*, never evidence: the gate re-derives every verdict (D-4), and the
mode a pull request runs under comes from its paths, not from what the block claims (F07-Q9). A
hand-opened pull request has no block at all and is gated identically, with its tooling recorded
as undeclared (R13).
"""

from __future__ import annotations

import json
from typing import Any

from opn_gate import bounce, schemas

MARKER = "opn-submission"
SCHEMA = "submission-meta/v1"
UNDECLARED = "undeclared"  # R13: what a hand-opened pull request's tooling is recorded as


def render_block(doc: dict[str, Any]) -> str:
    """What the service puts in the pull-request body."""
    return bounce.render_marked_block(MARKER, doc)


def extract(pr_body: str) -> dict[str, Any] | None:
    """The block's document, or ``None`` when there is none or it does not validate.

    A malformed block is the same as no block: it declares something the gate does not check, so
    refusing the submission over it would fail a proof for a formatting mistake (C7).
    """
    raw = bounce.extract_marked_block(MARKER, pr_body)
    if raw is None:
        return None
    try:
        doc = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if schemas.violations(doc, SCHEMA):
        return None
    assert isinstance(doc, dict)
    return doc


def model_and_tooling(doc: dict[str, Any] | None) -> str:
    """D-23's disclosure as one string, or ``undeclared`` (R13)."""
    tooling = (doc or {}).get("tooling") or {}
    parts = [str(tooling[k]) for k in ("model", "version", "harness") if tooling.get(k)]
    return " ".join(parts) if parts else UNDECLARED
