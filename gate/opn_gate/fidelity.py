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

**A certificate is for a statement, not a subject name** (F11-T9, finding C). ``fidelity/v2``
records the subject's content hash as it stood when the certificate was written — the value
F12's QA record pins, ``qa.subject_hash`` — and a certificate *counts* toward the grade, the
count and the names only if it is v2 and that hash is the subject's current one. A D-8 revision
of the root or an edit of a definition therefore drops the subject to ``mechanical-only`` with no
signers until someone signs the new statement (D-9: non-author sign-off is "the only event that
changes accepted state"); re-running the screens is not a signature and lifts nothing. A v1
certificate pins no statement and counts for nothing. Certificates that no longer count stay on
disk, because the record is append-only, and are simply not counted.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from opn_gate import schemas

log = logging.getLogger(__name__)

#: New certificates are written at v2, which pins the statement (F11-T9).
SCHEMA = "fidelity/v2"
#: Every version the reader accepts (D-34: versioned, never edited). v1 validates and loads — its
#: author still establishes the subject's — but it pins no statement, so it never counts.
READABLE_SCHEMAS: tuple[str, ...] = ("fidelity/v1", "fidelity/v2")
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
    schema: str = SCHEMA
    #: The subject's hash when the certificate was written; ``None`` on a v1 certificate.
    statement_hash: str | None = None

    @property
    def signs(self) -> bool:
        return is_signature(self.grade)

    def counts_for(self, current_hash: str | None) -> bool:
        """F11-T9: whether this certificate speaks for the subject as it stands. Only a v2
        certificate pins a statement, and only one pinned to the current hash counts; with no
        current hash (a definition that no longer exists) nothing does."""
        return (
            self.schema == SCHEMA
            and current_hash is not None
            and self.statement_hash == current_hash
        )


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
        doc = schemas.load_yaml(path)
        declared = doc.get("schema")
        if declared not in READABLE_SCHEMAS:
            msg = (
                f"{path}: schema {declared!r} is not a fidelity certificate; "
                f"readable: {', '.join(READABLE_SCHEMAS)}"
            )
            raise schemas.SchemaError(msg)
        hash_ = doc.get("statement_hash")
        cert = Certificate(
            subject=str(doc["subject"]),
            grade=str(doc["grade"]),
            attestor=str(doc["attestor"]),
            subject_author=str(doc["subject_author"]),
            date=str(doc["date"]),
            path=path,
            doc=doc,
            schema=str(declared),
            statement_hash=str(hash_) if hash_ is not None else None,
        )
        out.setdefault(cert.subject, []).append(cert)
    for certs in out.values():
        certs.sort(key=lambda c: (c.date, c.path.name))
    return out


def author_of(certs: list[Certificate]) -> str | None:
    """The subject's author on record: the first certificate's, of any version. Authorship is a
    fact about who wrote the subject, not a grade, so a v1 certificate still establishes it."""
    return certs[0].subject_author if certs else None


def current_hash(target_dir: Path, subject: str) -> str | None:
    """The subject's content hash as it stands — ``qa.subject_hash``, the value F12's QA record
    pins — or ``None`` for a certificate's subject that is no longer a definition of the target.

    A root that does not load raises (``qa.QaError``) rather than answering ``None``: the grade
    gates claiming, and a graph whose root cannot be read has a defect to fix, not a grade.
    """
    if subject not in subjects_of(target_dir):
        return None
    from opn_gate import qa  # noqa: PLC0415 — qa imports this module; the hash has one home

    return qa.subject_hash(target_dir, subject)


def counting(certs: list[Certificate], current: str | None) -> list[Certificate]:
    """F11-T9: the certificates that speak for the subject as it stands, oldest first."""
    return [cert for cert in certs if cert.counts_for(current)]


def grade_of(certs: list[Certificate]) -> str:
    """The grade of a list of *counting* certificates: the latest one's, or the default."""
    return certs[-1].grade if certs else DEFAULT_GRADE


def signers_of(certs: list[Certificate]) -> tuple[str, ...]:
    """Distinct attestors at ``screened-and-signed`` or above among *counting* certificates, in
    first-signature order."""
    seen: list[str] = []
    for cert in certs:
        if cert.signs and cert.attestor not in seen:
            seen.append(cert.attestor)
    return tuple(seen)


def _row(target_dir: Path, subject: str, certs: list[Certificate]) -> SubjectGrade:
    counted = counting(certs, current_hash(target_dir, subject)) if certs else []
    return SubjectGrade(
        subject=subject,
        grade=grade_of(counted),
        signers=signers_of(counted),
        author=author_of(certs),
    )


def subject_grades(target_dir: Path) -> list[SubjectGrade]:
    """One row per subject — the root and each definition that exists now — whether certified
    or not.

    Each row counts only the certificates for the subject as it stands (F11-T9). A certificate
    for a subject that is no longer a definition stays on disk and has no row: nothing can sign a
    subject that does not exist, so a row kept for it would hold the target below its root for
    good, while the root's own grade still bounds the target (Mike, 2026-09-13; F11-Q33).
    """
    certs = load(target_dir)
    return [_row(target_dir, s, certs.get(s, [])) for s in subjects_of(target_dir)]


def target_grade(target_dir: Path) -> str | None:
    """R3: the minimum over the root and every definition — or ``None`` when the target has no
    certificates at all, which is a pre-F11 target whose declaration still speaks for it."""
    if not load(target_dir):
        return None
    return min((row.grade for row in subject_grades(target_dir)), key=rank)


def meets(grade: str | None, wanted: str = CLAIMABLE_GRADE) -> bool:
    return grade is not None and rank(grade) >= rank(wanted)


def counting_signers(target_dir: Path) -> frozenset[str]:
    """F15-R5: every identity holding a counting signature on any subject of the target — the
    set the ledger bars from the proof line (D-9, D-21 v3.17). Empty for a target with no
    certificates, and for one whose every certificate is the machine's own grade."""
    if not load(target_dir):
        return frozenset()
    return frozenset(name for row in subject_grades(target_dir) for name in row.signers)


def prover_bar(graph_root: Path, target_dir: Path, attestor: str, grade: str) -> str | None:
    """F15-R5 (D-9 v3.17): why ``attestor`` may not sign ``target_dir`` at ``grade``, or ``None``
    — they hold an active proof line on the target, and a steward chooses to sign or to prove,
    never both. The machine's own grade signs for nobody and is never barred."""
    from opn_gate import ledger  # noqa: PLC0415 — the ledger reads this module's grades

    if not is_signature(grade) or not ledger.holds_proof_line(
        graph_root, attestor, target_dir.name
    ):
        return None
    return (
        f"{attestor!r} holds proof credit on {target_dir.name}, so they cannot attest its "
        f"fidelity at {grade!r}: whoever signs a statement takes no proof credit on the target, "
        "and whoever proved on it does not sign (D-9, D-21 v3.17; F15-R5)"
    )


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
    statement_hash: str,
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
        "statement_hash": statement_hash,
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


#: F12-R9: what stands between a signature and the record — called with the subject and the
#: grade before anything is written, for every grade from ``screened-and-signed`` up; it raises
#: to refuse. ``opn-gate fidelity`` wires it to the QA pass state and the exhibit replay
#: (``opn_gate.qa.grade_gate``); the library default is no gate, which is what intake's
#: ``mechanical-only`` certificate and the tests that build fixtures need (F12-Q15).
Gate = Callable[[str, str], object]


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
    gate: Gate | None = None,
) -> Path:
    """R3: append a certificate for ``subject``, refusing before anything is written.

    ``subject_author`` is taken from the subject's existing certificates when it has any — intake
    writes the first one and so establishes it — and must be given for a subject that has none.
    ``gate`` is F12-R9's refusal (see ``Gate``): it runs last, after the author rules, so a
    refused signature leaves nothing on disk (C7).
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
    if gate is not None and is_signature(grade):
        gate(subject, grade)
    hash_ = current_hash(target_dir, subject)
    assert hash_ is not None  # the subject was checked against subjects_of above
    doc = certificate_doc(
        subject=subject,
        statement_hash=hash_,
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
