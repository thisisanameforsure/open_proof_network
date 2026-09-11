"""Fidelity certificates and the grade they derive (F11-R3, R4; D-9 v3.12, D-6).

D-9 is a ladder, and what stands on each rung is a *statement* — the root's, and each definition
the root is stated over, because a definition that says the wrong thing makes a true theorem
about the wrong object. So the subject of a certificate is `root` or one name from the target's
``defs/``, and the target's grade is the **minimum** over all of them: a target is only as
faithful as its weakest definition.

Certificates live at ``targets/<id>/fidelity/<subject>-<n>.yaml`` and are append-only, like every
other record the graph keeps (D-34, C9). The latest by ``(date, file name)`` is a subject's
current grade; the ones underneath it stay, because a downgrade should show its history rather
than erase it.

Two rules are enforced here rather than trusted:

- **Above ``mechanical-only`` the attestor is not the author** (D-9: the second rung is a
  *non-author's* signature). ``mechanical-only`` is the machine's own grade and signs for nobody,
  so intake writes it in the author's name without tripping the rule.
- **A subject has one author.** The first certificate establishes it; a later one that names a
  different author is refused, because the two would be grading different things.

What a subject's certificates yield, besides the grade, is a *signature count and the names*
(D-9 v3.12: signatures are counted and named). Only certificates at ``screened-and-signed`` or
above count — a mechanical-only certificate is not a signature — and an attestor counts once
however often they sign.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from opn_gate import schemas

log = logging.getLogger(__name__)

SCHEMA = "fidelity/v1"
FIDELITY_DIR = "fidelity"
DEFS_DIR = "defs"
ROOT_SUBJECT = "root"
SUFFIXES: tuple[str, ...] = (".yaml", ".yml")

#: D-9 v3.12's ladder, low to high. Rung two is ``screened-and-signed``: v3.12 demoted
#: back-translation to one input of the rung because the 2026 evidence puts its false-pass rate
#: near a third.
GRADES: tuple[str, ...] = (
    "mechanical-only",
    "screened-and-signed",
    "author-attested",
    "expert-attested",
    "published-and-uncontested",
)
#: The rung a target must reach before its nodes may be claimed (D-6, F11-R4).
CLAIMABLE_GRADE = "screened-and-signed"
#: Below this rung a certificate is the machine's own: no signature, and no non-author rule.
SIGNED_FROM = "screened-and-signed"
DEFAULT_GRADE = GRADES[0]


class FidelityError(ValueError):
    """The certificate cannot be written, or the ones on disk do not agree. Nothing is written."""


def rank(grade: str) -> int:
    try:
        return GRADES.index(grade)
    except ValueError:
        msg = f"unknown fidelity grade {grade!r}; D-9's ladder is {', '.join(GRADES)}"
        raise FidelityError(msg) from None


def is_signature(grade: str) -> bool:
    return rank(grade) >= rank(SIGNED_FROM)


@dataclass(frozen=True)
class Certificate:
    """One certificate on disk, with where it came from."""

    subject: str
    grade: str
    attestor: str
    subject_author: str
    date: str
    path: Path
    doc: dict[str, Any]

    @property
    def signs(self) -> bool:
        return is_signature(self.grade)


@dataclass(frozen=True)
class SubjectGrade:
    """What a subject's certificate set says about it, in the shape the index publishes."""

    subject: str
    grade: str
    signers: tuple[str, ...]
    author: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "subject": self.subject,
            "grade": self.grade,
            "signature_count": len(self.signers),
            "signers": list(self.signers),
        }


# --- reading -----------------------------------------------------------------------------------


def fidelity_dir(target_dir: Path) -> Path:
    return target_dir / FIDELITY_DIR


def definitions(target_dir: Path) -> tuple[str, ...]:
    """The names of the target's own definitions: one per ``defs/*.lean`` (D-3).

    A definition file is a review object in its own right (D-9), so it is a fidelity subject
    whether or not anyone has certified it — an uncertified one holds the target at
    ``mechanical-only``, which is the point.
    """
    defs = target_dir / DEFS_DIR
    if not defs.is_dir():
        return ()
    return tuple(sorted(p.stem for p in defs.iterdir() if p.is_file() and p.suffix == ".lean"))


def subjects_of(target_dir: Path) -> tuple[str, ...]:
    return (ROOT_SUBJECT, *definitions(target_dir))


def load(target_dir: Path) -> dict[str, list[Certificate]]:
    """Every certificate, by subject, oldest first by ``(date, file name)``.

    A certificate that does not validate is a graph defect and raises: unlike an attempt record
    (F03-R7), a fidelity grade is load-bearing for claimability, so counting a broken one as
    "invalid" and carrying on would publish a grade nobody attested.
    """
    directory = fidelity_dir(target_dir)
    out: dict[str, list[Certificate]] = {}
    if not directory.is_dir():
        return out
    for path in sorted(p for p in directory.iterdir() if p.suffix in SUFFIXES):
        doc = schemas.load_yaml(path, SCHEMA)
        cert = Certificate(
            subject=str(doc["subject"]),
            grade=str(doc["grade"]),
            attestor=str(doc["attestor"]),
            subject_author=str(doc["subject_author"]),
            date=str(doc["date"]),
            path=path,
            doc=doc,
        )
        out.setdefault(cert.subject, []).append(cert)
    for certs in out.values():
        certs.sort(key=lambda c: (c.date, c.path.name))
    return out


def author_of(certs: list[Certificate]) -> str | None:
    return certs[0].subject_author if certs else None


def grade_of(certs: list[Certificate]) -> str:
    """The subject's current grade: the latest certificate's, or the default with none."""
    return certs[-1].grade if certs else DEFAULT_GRADE


def signers_of(certs: list[Certificate]) -> tuple[str, ...]:
    """Distinct attestors at ``screened-and-signed`` or above, in first-signature order."""
    seen: list[str] = []
    for cert in certs:
        if cert.signs and cert.attestor not in seen:
            seen.append(cert.attestor)
    return tuple(seen)


def subject_grades(target_dir: Path) -> list[SubjectGrade]:
    """One row per subject — the root and each definition — whether certified or not."""
    certs = load(target_dir)
    rows = [
        SubjectGrade(
            subject=subject,
            grade=grade_of(certs.get(subject, [])),
            signers=signers_of(certs.get(subject, [])),
            author=author_of(certs.get(subject, [])),
        )
        for subject in subjects_of(target_dir)
    ]
    # A certificate for a subject that is no longer a definition still names a real judgment;
    # publish it rather than dropping it, so a removed def cannot silently raise the grade.
    rows.extend(
        SubjectGrade(
            subject=subject,
            grade=grade_of(certs[subject]),
            signers=signers_of(certs[subject]),
            author=author_of(certs[subject]),
        )
        for subject in sorted(certs)
        if subject not in subjects_of(target_dir)
    )
    return rows


def target_grade(target_dir: Path) -> str | None:
    """R3: the minimum over the root and every definition — or ``None`` when the target has no
    certificates at all, which is a pre-F11 target whose declaration still speaks for it."""
    if not load(target_dir):
        return None
    return min((row.grade for row in subject_grades(target_dir)), key=rank)


def meets(grade: str | None, wanted: str = CLAIMABLE_GRADE) -> bool:
    return grade is not None and rank(grade) >= rank(wanted)


# --- writing -----------------------------------------------------------------------------------


def certificate_path(target_dir: Path, subject: str) -> Path:
    """``fidelity/<subject>-<n>.yaml`` for the next free ``n`` — append-only, never a rewrite."""
    directory = fidelity_dir(target_dir)
    taken = {p.name for p in directory.iterdir()} if directory.is_dir() else set()
    n = 1
    while f"{subject}-{n}.yaml" in taken:
        n += 1
    return directory / f"{subject}-{n}.yaml"


def certificate_doc(  # noqa: PLR0913 — one argument per fact the certificate records
    *,
    subject: str,
    grade: str,
    subject_author: str,
    attestor: str,
    date: str,
    evidence: str,
    evidence_files: tuple[str, ...] = (),
    exhibits: tuple[dict[str, Any], ...] = (),
) -> dict[str, Any]:
    doc: dict[str, Any] = {
        "schema": SCHEMA,
        "subject": subject,
        "grade": grade,
        "subject_author": subject_author,
        "attestor": attestor,
        "date": date,
        "evidence": evidence,
    }
    if evidence_files:
        doc["evidence_files"] = list(evidence_files)
    if exhibits:
        doc["exhibits"] = [dict(e) for e in exhibits]
    return schemas.validate(doc, SCHEMA)


def attest(  # noqa: PLR0913 — one argument per fact the certificate records
    target_dir: Path,
    subject: str,
    grade: str,
    *,
    attestor: str,
    date: str,
    evidence: str,
    subject_author: str | None = None,
    evidence_files: tuple[str, ...] = (),
    exhibits: tuple[dict[str, Any], ...] = (),
) -> Path:
    """R3: append a certificate for ``subject``, refusing before anything is written.

    ``subject_author`` is taken from the subject's existing certificates when it has any — intake
    writes the first one and so establishes it — and must be given for a subject that has none.
    """
    if not target_dir.is_dir():
        msg = f"no such target directory: {target_dir}"
        raise FidelityError(msg)
    known = subjects_of(target_dir)
    if subject not in known:
        msg = (
            f"{subject!r} is not a fidelity subject of this target; D-9's subjects are the root "
            f"and each definition: {', '.join(known)}"
        )
        raise FidelityError(msg)
    certs = load(target_dir).get(subject, [])
    on_record = author_of(certs)
    author = subject_author or on_record
    if author is None:
        msg = (
            f"{subject!r} has no certificate yet, so the subject's author is not on record; "
            "pass it explicitly"
        )
        raise FidelityError(msg)
    if on_record is not None and subject_author is not None and subject_author != on_record:
        msg = (
            f"{subject!r} is on record as authored by {on_record!r}, not {subject_author!r}; "
            "a subject has one author (D-9)"
        )
        raise FidelityError(msg)
    if is_signature(grade) and attestor == author:
        msg = (
            f"{attestor!r} authored {subject!r}, so they cannot attest it at {grade!r}: "
            f"every rung from {SIGNED_FROM} up is a non-author's signature (D-9)"
        )
        raise FidelityError(msg)
    doc = certificate_doc(
        subject=subject,
        grade=grade,
        subject_author=author,
        attestor=attestor,
        date=date,
        evidence=evidence,
        evidence_files=evidence_files,
        exhibits=exhibits,
    )
    path = certificate_path(target_dir, subject)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True), encoding="utf-8")
    log.info("fidelity: %s is %s, attested by %s", subject, grade, attestor)
    return path
