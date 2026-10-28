"""The background opening of a formalization review (F26-R2; D-9 v3.39).

For every target that exists at the re-pin the network opens a review whatever
``policy.json``'s ``review_openers`` says, with the live statement as the first candidate: the
curator's command ``opn-gate review open --graph <checkout> --target <id> | --all`` writes
``targets/<id>/review/review.yaml`` (``review/v1``, opened by ``network``) and the root's
``Statement.lean`` as ``review/candidates/c-<8 hex>.yaml`` beside a byte copy of the Lean
(``candidate/v1``, ``origin: ported``). Nothing is pushed or committed: the curator commits what
was written, directly — a ``network`` opening is never admitted by pull request
(``modes.check_review_opening``). The live text and hash are untouched (R2); the wrapper the
format rule may add is F26-T4's.

Idempotent: a target with a ``review.yaml`` is left alone and the summary says so.
"""

from __future__ import annotations

import hashlib
import logging
import re
from pathlib import Path
from typing import Any

import yaml

from opn_gate import admit, intake, ledger, review, schemas
from opn_gate.paths import REVIEW_DIR

log = logging.getLogger(__name__)

#: The opener of the background review (``review/v1``'s ``opened_by.role``).
NETWORK = "network"
#: The author a ported candidate is credited to when no ledger names a statement line for the
#: root: the curator who seeded the statement (D-21 bars them from proof credit, not from this).
CURATOR_AUTHOR = "curator"
#: The first doc comment of a Lean file (``/-! … -/`` or ``/-- … -/``), the root's words when the
#: target record holds no informal statement. A plain ``/- … -/`` is not one: a registry import
#: opens with its licence header, which was taken for the words (2026-10-28, F-A4).
_DOC_COMMENT_RE = re.compile(r"\A\s*/-[!-]\s*(?P<text>.*?)\s*-/", re.S)


def target_ids(graph_root: Path) -> list[str]:
    """Every target with a ``gate-spec.json``, in name order (the 2026-09-17 lesson: key a
    target loop on the spec, since ``targets/`` also holds ``index.json``)."""
    return sorted(p.parent.name for p in (graph_root / "targets").glob("*/gate-spec.json"))


def open_review(graph_root: Path, target_id: str, *, day: str) -> dict[str, Any]:
    """Open the background review of ``target_id`` in the checkout, or say why not.

    One summary per target: ``{"target", "ok", "root", "written", "skipped"}`` — ``written`` the
    paths from the graph root (empty when nothing was), ``skipped`` the reason nothing was, or
    ``{"target", "ok": False, "error", "written": []}`` for a target whose root or words cannot be
    found, with nothing written (C7).
    """
    target_dir = graph_root / "targets" / target_id
    if not target_dir.is_dir():
        return _error(target_id, f"no such target directory: targets/{target_id}")
    if review.opening(target_dir) is not None:
        return {
            "target": target_id,
            "ok": True,
            "root": None,
            "written": [],
            "skipped": "a review exists; nothing written",
        }
    root = admit.root_of(graph_root, target_id)
    if root is None:
        return _error(
            target_id, "no root: the target declares none and more than one node is undepended-on"
        )
    statement = target_dir / "nodes" / root / "Statement.lean"
    if not statement.is_file():
        return _error(target_id, f"root {root!r} has no Statement.lean")
    lean = statement.read_bytes()
    words = words_for(target_dir, lean)
    if words is None:
        return _error(
            target_id,
            f"no words: target.yaml holds no informal statement and {root}'s Statement.lean "
            "has no doc comment",
        )
    digest = hashlib.sha256(lean).hexdigest()
    cid = f"c-{digest[:8]}"
    head = schemas.validate(
        {
            "schema": "review/v1",
            "target": target_id,
            "opened_by": {"identity": NETWORK, "role": NETWORK},
            "date": day,
            "words": words,
            "cases": [],
            "concepts": [],
            "source": {"kind": "existing", "ref": root},
            "tracking": None,
            "supersedes": None,
        },
        "review/v1",
    )
    candidate = schemas.validate(
        {
            "schema": "candidate/v1",
            "target": target_id,
            "id": cid,
            "author": statement_author(graph_root, target_id, root) or CURATOR_AUTHOR,
            "method": "other",
            "models": [],
            "read_others": None,
            "origin": "ported",
            "source": {"kind": "existing", "ref": root},
            "lean_file": f"{cid}.lean",
            "statement_hash": digest,
            "date": day,
        },
        "candidate/v1",
    )
    base = target_dir / REVIEW_DIR
    candidates = base / "candidates"
    candidates.mkdir(parents=True, exist_ok=True)
    written = [
        _write_yaml(base / "review.yaml", head),
        _write_yaml(candidates / f"{cid}.yaml", candidate),
        candidates / f"{cid}.lean",
    ]
    written[-1].write_bytes(lean)
    log.info("review: opened the background review of %s on %s as %s", target_id, root, cid)
    return {
        "target": target_id,
        "ok": True,
        "root": root,
        "written": [p.relative_to(graph_root).as_posix() for p in written],
        "skipped": None,
    }


def words_for(target_dir: Path, lean: bytes) -> str | None:
    """The conjecture in words: ``target.yaml``'s informal statement when the target has one,
    else the root statement's doc comment, else the record's paraphrase (a source the network
    may not reproduce leaves ``informal`` null, F11-R10), else ``None``."""
    record: dict[str, Any] | None
    try:
        record = intake.load_doc(target_dir)
    except schemas.SchemaError as exc:
        log.warning(
            "%s: target.yaml does not read; the words come from the statement: %s",
            target_dir.name,
            exc,
        )
        record = None
    informal = (record or {}).get("informal")
    if isinstance(informal, str) and informal.strip():
        return informal.strip()
    comment = doc_comment(lean)
    if comment:
        return comment
    paraphrase = (record or {}).get("paraphrase")
    if isinstance(paraphrase, str) and paraphrase.strip():
        return paraphrase.strip()
    return None


def doc_comment(lean: bytes) -> str | None:
    """The text of the first doc comment of a Lean file, or ``None``."""
    try:
        text = lean.decode("utf-8")
    except UnicodeDecodeError:
        return None
    m = _DOC_COMMENT_RE.match(text)
    found = m.group("text").strip() if m else ""
    return found or None


def statement_author(graph_root: Path, target_id: str, root: str) -> str | None:
    """The identity holding an active statement line for the root, from the ledger (D-19), or
    ``None``; asked of every ledger as ``ledger.writeup_holder`` is."""
    for identity, entries in ledger.contributions(graph_root).items():
        for e in entries:
            if (
                e.get("line") == "statement"
                and e.get("target") == target_id
                and e.get("node") == root
                and e.get("status") == "active"
            ):
                return identity
    return None


def _write_yaml(path: Path, doc: dict[str, Any]) -> Path:
    path.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return path


def _error(target_id: str, error: str) -> dict[str, Any]:
    return {"target": target_id, "ok": False, "error": error, "written": []}
