"""The formalization review's derived state (F26-R1, R17; D-9 v3.39).

Nothing here is written: the records under ``targets/<id>/review/`` are the facts, and every
reader derives the same state from them in any order. T1 publishes the contract — the shape the
products carry — with the derivation the records support today (counts, questions waiting, the
tracking pointer); T2 adds clusters, survivors, the ladder and the signers from exhibits, pairs
and signatures.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from opn_gate.paths import REVIEW_DIR

#: The review states the products publish.
NONE, OPEN, NEEDS_INTENT, COMPLETE = "none", "open", "needs-intent-signer", "complete"


def _records(folder: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not folder.is_dir():
        return out
    for path in sorted(folder.iterdir()):
        if path.suffix not in (".yaml", ".yml"):
            continue
        try:
            doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError):
            continue
        if isinstance(doc, dict):
            out.append(doc)
    return out


def opening(target_dir: Path) -> dict[str, Any] | None:
    """``review.yaml`` as a document, or ``None`` for a target with no review."""
    path = target_dir / REVIEW_DIR / "review.yaml"
    if not path.is_file():
        return None
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return None
    return doc if isinstance(doc, dict) else None


def questions_waiting(target_dir: Path) -> list[dict[str, Any]]:
    """The questions no answer record names, in the records' order."""
    base = target_dir / REVIEW_DIR
    answered = {str(a.get("question")) for a in _records(base / "answers")}
    return [q for q in _records(base / "questions") if str(q.get("id")) not in answered]


def state_of(target_dir: Path) -> dict[str, Any]:
    """The ``review`` object ``targets-index`` and ``graph.json`` carry (F26-R17)."""
    head = opening(target_dir)
    empty = {
        "state": NONE,
        "candidates": 0,
        "surviving": 0,
        "clusters": 0,
        "questions_waiting": 0,
        "open_pairs": 0,
        "grade_cap": None,
        "signers": {"intent": None, "independent": None},
        "tracking": None,
    }
    if head is None:
        return empty
    base = target_dir / REVIEW_DIR
    candidates = _records(base / "candidates")
    waiting = questions_waiting(target_dir)
    pairs = _records(base / "pairs")
    open_pairs = sum(
        1
        for p in pairs
        for d in ("forward", "backward")
        if isinstance(p.get(d), dict) and p[d].get("state") == "open"
    )
    signers: dict[str, str | None] = {"intent": None, "independent": None}
    for s in _records(base / "signatures"):
        role = str(s.get("role"))
        if role in signers and s.get("decision") == "accept":
            signers[role] = str(s.get("login"))
    return {
        **empty,
        "state": OPEN,
        "candidates": len(candidates),
        "surviving": len(candidates),  # T2: minus the discarded and the returned, from exhibits
        "questions_waiting": len(waiting),
        "open_pairs": open_pairs,
        "signers": signers,
        "tracking": head.get("tracking"),
    }


def open_pairs(target_dir: Path) -> list[dict[str, str]]:
    """``graph.json``'s ``open_pairs`` (F26-R8): each open direction, in the records' order."""
    out: list[dict[str, str]] = []
    for p in _records(target_dir / REVIEW_DIR / "pairs"):
        for direction in ("forward", "backward"):
            d = p.get(direction)
            if isinstance(d, dict) and d.get("state") == "open":
                out.append({"a": str(p.get("a")), "b": str(p.get("b")), "direction": direction})
    return out


def for_context(target_dir: Path) -> dict[str, Any] | None:
    """``CONTEXT.json``'s ``review`` for the root node (F26-R17): the state, the words and the
    questions waiting; ``None`` for a target with no review."""
    head = opening(target_dir)
    if head is None:
        return None
    return {
        "state": state_of(target_dir)["state"],
        "words": str(head.get("words") or ""),
        "questions_waiting": [
            {"id": str(q.get("id")), "question": str(q.get("question") or "")}
            for q in questions_waiting(target_dir)
        ],
    }
