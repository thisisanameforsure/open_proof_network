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
from dataclasses import dataclass
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


# --- what a merged partial leaves behind (F07-R6, R7; D-12, D-29, D-31) --------------------------
#
# A partial proof is the one artifact that merges without resolving anything: the assembly is
# kernel-checked, the holes are not, and D-29's rule is that those holes become nodes with no
# human deciding they should. So this is where a submission turns into structure — the only
# place in the gate that writes node directories that nobody proposed.
#
# Everything here is a pure function of the merged tree plus the hole report, so the workflow
# feeds it what the gate already computed and the tests need neither GitHub nor Lean.

ANNEX_DIR = "annex"
ATTEMPTS_DIR = "attempts"
CHILD_SEPARATOR = "--h"
PARTIAL_SUFFIX = "-partial.lean"
ALTERNATE_SUFFIX = "-alternate.lean"
#: D-31 v3.12: the skeleton names its annex in the file, as a comment, so the gate re-derives the
#: citation from evidence instead of trusting a declaration.
_ANNEX_LINE_RE = re.compile(r"^\s*--\s*annex:\s*(?P<hash>[0-9a-f]{64})\s*$", re.M)
DAY_CHARS = 8  # YYYYMMDD, the prefix of a compact timestamp
ORIGIN_COMPILER = "compiler-derived"
ORIGIN_SKELETON = "skeleton-hole"
#: R6: the child is created with a witness slot. Until someone fills it the node is blocked, and
#: F03 derives that from this file rather than from a record (graph.witness_is_stub).
WITNESS_SLOT = (
    "/-! The witness slot for a hole (D-29, F07-R6). Replace `sorry` with an instance\n"
    "satisfying this statement's hypotheses; until then the node is blocked. -/\n\n"
    "theorem witness : {expected} := by\n  sorry\n"
)


def annex_citation(partial_text: str) -> str | None:
    """The annex hash a skeleton cites, or ``None`` when the file cites none (D-31 v3.12)."""
    m = _ANNEX_LINE_RE.search(partial_text)
    return m.group("hash") if m else None


def annex_present(node_dir: Path, digest: str) -> bool:
    return (node_dir / ANNEX_DIR / f"{digest}.md").is_file()


def check_annex_citation(node_dir: Path, partial_text: str) -> Diagnostic | None:
    """R6: a cited annex that is not on the node is a rejection, not a missing footnote.

    The citation is what makes D-31's reuse mechanical — it is how prose that helped becomes
    traceable from the node it helped — so a citation pointing at nothing is worse than none.
    """
    digest = annex_citation(partial_text)
    if digest is None or annex_present(node_dir, digest):
        return None
    return Diagnostic(
        "annex-uncited",
        f"the skeleton cites annex {digest[:12]}…, which is not on this node; submit the annex "
        "first and cite the hash it returns (D-31)",
        {"annex": digest},
    )


def child_origin(partial_text: str) -> str:
    """R6, D-3 v3.12: a hole from a cited skeleton is its own origin, not compiler-derived.

    The elaborator did not choose these statements — a person did, by writing the decomposition —
    and D-25 has always published ``skeleton-hole`` as a filterable frontier value.
    """
    return ORIGIN_SKELETON if annex_citation(partial_text) is not None else ORIGIN_COMPILER


def child_id(parent: str, index: int) -> str:
    """R6: ``<parent>--h<n>``, one-based, stable in the order the holes were extracted."""
    return f"{parent}{CHILD_SEPARATOR}{index}"


def child_statement(child: str, hole: Any) -> str:
    """The child's ``Statement.lean``: the hole's obligation, closed over the binders it sat under.

    The closed form is what makes it a node at all — a hole typed ``q`` inside ``∀ p q, …`` is not
    a proposition anyone can state on its own (F07-T4, from the extractor's ``closed_type``).
    """
    decl = child.replace("-", "_")
    return (
        f"/-! Hole `{hole.name}` of a merged partial proof, as a node (D-12 #5, D-29).\n"
        "Statement generated by the gate from the assembly; immutable (D-3). -/\n\n"
        f"theorem {decl} : {hole.closed_type} := by\n  sorry\n"
    )


@dataclass(frozen=True)
class PartialMerge:
    """What a merged partial produced: the children, and where the assembly was filed."""

    children: tuple[str, ...]
    attempt_path: str
    origin: str
    annex: str | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "children": list(self.children),
            "attempt": self.attempt_path,
            "origin": self.origin,
            "annex": self.annex,
        }


def attempt_name(stamp: str, pseudonym: str, suffix: str) -> str:
    """``<ts>-<pseudonym>-partial.lean`` / ``-alternate.lean`` (R6, R7; D-13's shape)."""
    return f"{stamp}-{pseudonym}{suffix}"


def record_attempt(node_dir: Path, name: str, text: str) -> str:
    """File a submission under ``attempts/`` — append-only, so an existing name is a refusal."""
    attempts = node_dir / ATTEMPTS_DIR
    attempts.mkdir(parents=True, exist_ok=True)
    dest = attempts / name
    if dest.exists():
        msg = f"{dest.name} already exists; attempts/ is append-only (D-3)"
        raise GraphWriteError(msg)
    dest.write_text(text, encoding="utf-8")
    return f"{ATTEMPTS_DIR}/{name}"


class GraphWriteError(RuntimeError):
    """The post-merge job cannot write what it was asked to; nothing is left half-written."""


def apply_partial(  # noqa: PLR0913 — the merge's facts, each named
    node_dir: Path,
    holes: Sequence[Any],
    *,
    partial_text: str,
    pseudonym: str,
    stamp: str,
    author: str | None = None,
) -> PartialMerge:
    """R6: turn a merged partial into child nodes, and file the assembly under ``attempts/``.

    Order matters and is chosen so a failure leaves nothing behind: the citation is checked, then
    the children are written, then the parent's ``deps`` and ``Context.lean`` are regenerated to
    match, then the assembly is filed. The parent's statement is never touched — only the two
    bot-owned files change, which is what keeps D-3's immutability intact (F07-Q2).
    """
    from opn_gate import scaffold  # noqa: PLC0415 — scaffold imports layout, which imports schemas

    problem = check_annex_citation(node_dir, partial_text)
    if problem is not None:
        raise GraphWriteError(problem.message)
    if not holes:
        msg = "a partial with no holes creates no children (D-12 #5)"
        raise GraphWriteError(msg)

    origin = child_origin(partial_text)
    annex = annex_citation(partial_text)
    nodes_dir = node_dir.parent
    parent = node_dir.name
    created: list[str] = []
    for index, hole in enumerate(holes, start=1):
        child = child_id(parent, index)
        statement = child_statement(child, hole)
        proposal = scaffold.Proposal(
            node_id=child,
            target_id=nodes_dir.parent.name,
            statement=statement,
            witness=WITNESS_SLOT.format(expected="True"),
            author=author or pseudonym,
            origin=origin,  # type: ignore[arg-type]
            date=stamp_to_date(stamp),
        )
        scaffold.write(nodes_dir, proposal)
        created.append(child)

    add_deps(node_dir, created)
    regenerate_context(node_dir, nodes_dir)
    attempt = record_attempt(node_dir, attempt_name(stamp, pseudonym, PARTIAL_SUFFIX), partial_text)
    return PartialMerge(tuple(created), attempt, origin, annex)


def stamp_to_date(stamp: str) -> str:
    """``20260910T121314Z`` -> ``2026-09-10``, the day META records."""
    return f"{stamp[0:4]}-{stamp[4:6]}-{stamp[6:8]}" if len(stamp) >= DAY_CHARS else stamp


def add_deps(node_dir: Path, children: Sequence[str]) -> list[str]:
    """R6, Q2: append the new node ids to the parent's ``deps``. Bot-owned, and additive — the
    statement hash is untouched, so the node's immutability is not what changes here."""
    import yaml  # noqa: PLC0415 — only the writing path needs it

    meta_path = node_dir / "META.yaml"
    meta = yaml.safe_load(meta_path.read_text(encoding="utf-8"))
    deps = [str(d) for d in (meta.get("deps") or [])]
    for child in children:
        if child not in deps:
            deps.append(child)
    meta["deps"] = deps
    dumped = yaml.safe_dump(meta, sort_keys=False, allow_unicode=True)
    meta_path.write_text(dumped, encoding="utf-8")
    return deps


def regenerate_context(node_dir: Path, nodes_dir: Path) -> str:
    """R6, Q2: rewrite the parent's ``Context.lean`` from its declared deps.

    Generated rather than edited, for the reason the scaffold generates it: F01-R6 compares each
    signature here with the dep's own ``Statement.lean``, byte for byte.
    """
    import yaml  # noqa: PLC0415

    from opn_gate import scaffold  # noqa: PLC0415

    meta = yaml.safe_load((node_dir / "META.yaml").read_text(encoding="utf-8"))
    deps = tuple(str(d) for d in (meta.get("deps") or []))
    text = scaffold.context_for(nodes_dir, deps)
    (node_dir / "Context.lean").write_text(text, encoding="utf-8")
    return text


def record_alternate(node_dir: Path, proof_text: str, *, pseudonym: str, stamp: str) -> str:
    """R7, D-25: a second proof of an already-proved node is recorded, not merged over the first.

    Racing is permitted and on hard nodes desirable, so the loser's work is kept — but
    ``Proof.lean`` is the first one that landed and this never touches it.
    """
    return record_attempt(node_dir, attempt_name(stamp, pseudonym, ALTERNATE_SUFFIX), proof_text)
