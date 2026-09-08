"""The post-merge job's pure parts (F00-R14, Q4, Q8; C8 item 1).

After a pull request merges to ``main``, a separate job re-runs the gate on the merge commit,
fills ``merge_commit`` and the step-9 ``review`` block (D-4 v3.11: the tutorial exemption, a
non-author PR approval, or the statement's certificate/provenance), signs the record with the
gate key, and commits it to
``attestations/<id>.json``. Everything here is testable without GitHub: the workflow only feeds
it the merge commit, the pull-request number, the reviews list and the key path.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Literal

from opn_gate import attestation, schemas
from opn_gate.signer import Signer

ID_WIDTH = 6
_MERGE_RE = re.compile(r"^Merge pull request #(?P<n>\d+)\b")
_SQUASH_RE = re.compile(r"\(#(?P<n>\d+)\)\s*$", re.M)


def attestation_id(pr_number: int) -> str:
    """Q8: the merged PR number, zero-padded, unique per graph repo and human-readable."""
    if pr_number <= 0:
        msg = f"pull request number must be positive, got {pr_number}"
        raise ValueError(msg)
    return f"{pr_number:0{ID_WIDTH}d}"


def attestation_path(graph_root: Path, pr_number: int) -> Path:
    return graph_root / "attestations" / f"{attestation_id(pr_number)}.json"


def pr_number_from_message(message: str) -> int | None:
    """The PR number a merge commit's message names (merge commits and squash merges)."""
    first = message.splitlines()[0] if message else ""
    m = _MERGE_RE.match(first)
    if m:
        return int(m.group("n"))
    m = _SQUASH_RE.search(first)
    return int(m.group("n")) if m else None


def approving_reviewer(reviews: list[dict[str, Any]], author: str) -> str | None:
    """D-4 step 9: the latest APPROVED review by an identity other than the author."""
    approved = [
        r
        for r in reviews
        if r.get("state") == "APPROVED" and (r.get("user") or {}).get("login") not in (None, author)
    ]
    if not approved:
        return None
    approved.sort(key=lambda r: str(r.get("submitted_at", "")))
    login = approved[-1]["user"]["login"]
    return str(login)


ReviewKind = Literal["tutorial", "pr-approval", "certificate", "provenance"]


def review_block(
    kind: ReviewKind, *, reviewer: str | None = None, reference: str | None = None
) -> dict[str, Any]:
    """The step-9 record (D-4 v3.11): what stood behind the merge."""
    if kind == "pr-approval" and not reviewer:
        msg = "a pr-approval review needs the approving reviewer's identity"
        raise ValueError(msg)
    if kind in ("certificate", "provenance") and not reference:
        msg = f"a {kind} review needs a reference"
        raise ValueError(msg)
    return {"kind": kind, "reviewer": reviewer, "reference": reference}


def record_step9(
    doc: dict[str, Any], *, merge_commit: str, review: dict[str, Any]
) -> dict[str, Any]:
    """Fill the post-merge fields; the record stays unsigned until ``sign_gate``."""
    out = dict(doc)
    out["runner"] = "hosted"
    out["merge_commit"] = merge_commit
    out["review"] = review
    return schemas.validate(out, attestation.SCHEMA)


def sign_gate(doc: dict[str, Any], *, key_path: Path, signer: Signer) -> dict[str, Any]:
    """Sign with the gate key (signature kind ``gate``); the seal time is kept."""
    out = dict(doc)
    sig = signer.sign(attestation.signed_bytes(out), key_path, "gate")
    out["signature"] = {
        "kind": "gate",
        "key_id": sig.key_id,
        "value": sig.value,
        "timestamp": doc["signature"]["timestamp"],
    }
    return schemas.validate(out, str(doc["schema"]))


def finalize(
    doc: dict[str, Any],
    *,
    merge_commit: str,
    review: dict[str, Any],
    key_path: Path,
    signer: Signer,
) -> dict[str, Any]:
    """Fill the post-merge fields and sign with the gate key."""
    return sign_gate(
        record_step9(doc, merge_commit=merge_commit, review=review),
        key_path=key_path,
        signer=signer,
    )


def verify(doc: dict[str, Any], public_key: str, signer: Signer) -> bool:
    """Check a committed attestation's signature against the committed gate public key."""
    sig = doc.get("signature") or {}
    if sig.get("kind") not in ("gate", "service", "contributor") or not sig.get("value"):
        return False
    if sig.get("key_id") != signer.fingerprint(public_key):
        return False
    return signer.verify(attestation.signed_bytes(doc), str(sig["value"]), public_key)
