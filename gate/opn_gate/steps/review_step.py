"""D-4 step 9 reads the formalization review (F26-R12; D-4 v3.39).

A proof that would settle a target's root merges only when that target's review is complete —
the automated stages done, no question waiting, the grade at least ``screened-and-signed`` — or
when v3.15's recorded catalog evidence scores at least five points (``modes.step9_evidence``,
unchanged). Intermediate work never consults the review: ``modes.step9_not_asked`` answers first.
A target with no review keeps the rule it had before v3.39 exactly, so nothing live moves until
reviews exist (F26-Q7).

This module is the review's basis alone, beside the certificate and the evidence in
``modes.with_statement_review``: each is one named function, so reversing one is a deletion.
Step 9 is not a pipeline step (it runs at classification, before any sandbox), so nothing here is
a ``Step``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from opn_gate import fidelity, review
from opn_gate.diagnostic import Diagnostic
from opn_gate.paths import REVIEW_DIR

log = logging.getLogger(__name__)

#: The code a proof that would settle the root carries while its target's review is incomplete.
HELD_CODE = "review-incomplete"
#: D-4 v3.11's rung, which v3.39 asks of the review too ("grade at least screened-and-signed").
STEP9_GRADE = fidelity.SIGNED_FROM
#: The state a review that cannot be read stands in, for the verdict's details.
UNREADABLE = "unreadable"


@dataclass(frozen=True)
class Standing:
    """Where a target's review stands for step 9: its derived ``state``, the words a verdict
    names it by, and the ``reference`` an attestation cites — set exactly when the review
    satisfies step 9."""

    state: str
    words: str
    reference: str | None = None

    @property
    def satisfies(self) -> bool:
        return self.reference is not None


def standing(target_dir: Path) -> Standing | None:
    """The review's standing for step 9, or ``None`` for a target with no review (F26-Q7).

    Satisfied exactly when the review is ``complete`` (one reading survives, no question waits)
    and the grade it stands at is at least ``screened-and-signed``. A review that does not read
    holds: nothing stands in for a person on a guess (C7)."""
    try:
        summary = review.state_of(target_dir)
    except (ValueError, OSError) as exc:  # SchemaError, a malformed record: a graph defect
        log.warning("step 9: the review of %s does not read, so it holds: %s", target_dir.name, exc)
        return Standing(UNREADABLE, "the review does not read")
    state = str(summary["state"])
    if state == review.NONE:
        return None
    if state != review.COMPLETE:
        return Standing(state, words(summary))
    grade = review_grade(target_dir)
    if not fidelity.meets(grade, STEP9_GRADE):
        return Standing(state, f"review complete at {grade}, below {STEP9_GRADE}")
    return Standing(state, f"review complete at {grade}", reference(target_dir, grade))


def words(summary: dict[str, Any]) -> str:
    """An incomplete review's state as a verdict names it: what it is waiting on."""
    waiting = int(summary["questions_waiting"])
    asked = f"{waiting} question{'' if waiting == 1 else 's'} waiting"
    if summary["state"] == review.NEEDS_INTENT:
        return f"review needs an intent signer: {asked}"
    if waiting:
        return f"review open: {asked}"
    clusters = int(summary["clusters"])
    if clusters == 0:
        return "review open: no candidate survives"
    return f"review open: {clusters} readings survive"


def review_grade(target_dir: Path) -> str:
    """The grade the review stands at (``review.grade_of``, D-9 v3.39's ladder), never below the
    root's counting certificates' grade — the grade the certificate basis reads (F11-R3)."""
    certs = fidelity.load(target_dir).get(fidelity.ROOT_SUBJECT, [])
    current = fidelity.current_hash(target_dir, fidelity.ROOT_SUBJECT)
    held_grade = fidelity.grade_of(fidelity.counting(certs, current))
    return review.grade_of(target_dir, held_grade)


def reference(target_dir: Path, grade: str) -> str:
    """What an attestation cites when the review stood in for a person: the review, the root
    statement it was about and the grade, in the evidence reference's shape (F14-R6)."""
    root_hash = fidelity.current_hash(target_dir, fidelity.ROOT_SUBJECT)
    about = f"@{root_hash}" if root_hash else ""
    return f"review:{REVIEW_DIR}/review.yaml{about}:{grade}"


def held(target_id: str, standing: Standing, *, minimum: int) -> Diagnostic:
    """The verdict while step 9 holds: the review's state by name, and what would let it merge."""
    return Diagnostic(
        HELD_CODE,
        f"step 9: this proof would settle the root of {target_id}, and the target's "
        f"formalization review is not complete ({standing.words}); it merges once the review is "
        f"complete at screened-and-signed or above, or on recorded catalog evidence scoring at "
        f"least {minimum} (D-4 v3.39). Nothing is wrong with the proof for this: re-run the "
        "gate on the pull request once the review is complete.",
        {"target": target_id, "review_state": standing.state, "review": standing.words},
    )
