"""The post-merge job's pure parts (F00-R14, Q4, Q8; C8 item 1).

After a pull request merges to ``main``, a separate job re-runs the gate on the merge commit,
fills ``merge_commit`` and the step-9 ``review`` block (D-4 v3.11: the tutorial exemption, a
non-author PR approval, or the statement's certificate/provenance), signs the record with the
gate key, and commits it to
``attestations/<id>.json``. Everything here is testable without GitHub: the workflow only feeds
it the merge commit, the pull-request number, the reviews list and the key path.
"""

from __future__ import annotations

import json
import logging
import re
import urllib.request
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any, Literal

from opn_gate import attestation, schemas
from opn_gate.diagnostic import Diagnostic
from opn_gate.signer import Signer

log = logging.getLogger(__name__)

ID_WIDTH = 6
_MERGE_RE = re.compile(r"^Merge pull request #(?P<n>\d+)\b")
_SQUASH_RE = re.compile(r"\(#(?P<n>\d+)\)\s*$", re.M)
WAIVER_LINE = "waiver: native_decide"  # F02-R9: what the approving review must say
_WAIVER_LINE_RE = re.compile(r"^\s*" + re.escape(WAIVER_LINE) + r"\s*$", re.M)


def approval_names_waiver(body: str) -> bool:
    """True when a review body contains the line ``waiver: native_decide`` (F02-R9)."""
    return bool(_WAIVER_LINE_RE.search(body or ""))


def check_waiver(doc: dict[str, Any], approval_bodies: Sequence[str]) -> Diagnostic | None:
    """F02-R9: a waived proof (``trust_base: compiler``) merges only if the approving review
    names the waiver; otherwise the post-merge job refuses with this diagnostic."""
    if doc.get("trust_base") != attestation.TRUST_COMPILER:
        return None
    if any(approval_names_waiver(b) for b in approval_bodies):
        return None
    return Diagnostic(
        "waiver-unapproved",
        "the proof used native_decide under a waiver, but no approving review names it; the "
        f"reviewer must include the line `{WAIVER_LINE}` in the approval",
        {"required_line": WAIVER_LINE, "approvals_seen": len(approval_bodies)},
    )


_BOT_MESSAGE_RE = re.compile(r"^gate: #(?P<n>\d+) (?P<verdict>pass|fail)$")
PRODUCT_FILES: tuple[str, ...] = ("frontier.json", "info.json", "targets/index.json")
CLAIMS_FILE = "claims.json"
CLAIMS_TIMEOUT_S = 10


def fetch_claims_snapshot(url: str, *, opener: Callable[[str, int], bytes] | None = None) -> bytes:
    """F05-R10: ``GET /claims.json`` from the service, as raw bytes.

    Raises ``OSError`` or ``ValueError`` on any failure; the caller falls back (C7).
    """
    if not url.startswith(("https://", "http://127.0.0.1", "http://localhost")):
        msg = f"the claims endpoint must be https (or a local runner): {url}"
        raise ValueError(msg)
    if opener is not None:
        return opener(url, CLAIMS_TIMEOUT_S)
    request = urllib.request.Request(url, headers={"User-Agent": "opn-gate"})  # noqa: S310
    with urllib.request.urlopen(request, timeout=CLAIMS_TIMEOUT_S) as resp:  # noqa: S310
        body: bytes = resp.read()
    return body


def refresh_claims(
    graph_root: Path, url: str | None, *, opener: Callable[[str, int], bytes] | None = None
) -> str | None:
    """Write ``claims.json`` from the service, keeping the committed one on any failure.

    Returns ``None`` when the snapshot was refreshed, else the reason the previous file stands
    (F05-R10, AC16: the service is never allowed to block a merge).
    """
    if not url:
        return "no claims endpoint configured"
    try:
        body = fetch_claims_snapshot(url, opener=opener)
        doc = schemas.validate(json.loads(body), "claims/v1")
    except (OSError, ValueError, schemas.SchemaError) as exc:
        reason = f"{type(exc).__name__}: {exc}"
        log.warning(
            "claims snapshot unavailable (%s); keeping the committed %s", reason, CLAIMS_FILE
        )
        return reason
    (graph_root / CLAIMS_FILE).write_bytes(schemas.canonical_json(doc))
    return None


def bot_commit_message(pr_number: int, verdict: str) -> str:
    """F03-R12: the one bot commit carrying the attestation and every product."""
    if verdict not in ("pass", "fail"):
        msg = f"a bot commit records pass or fail, not {verdict!r}"
        raise ValueError(msg)
    return f"gate: #{attestation_id(pr_number).lstrip('0') or '0'} {verdict}"


def parse_bot_commit_message(message: str) -> tuple[int, str] | None:
    """The (pr, verdict) a bot commit's first line names, or ``None`` for any other commit."""
    first = message.splitlines()[0] if message else ""
    m = _BOT_MESSAGE_RE.match(first)
    return (int(m.group("n")), m.group("verdict")) if m else None


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
