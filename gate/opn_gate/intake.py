"""Curated intake: the target record, its checks, and the two acts that make it claimable
(F11-R1, R2, R4, R5; D-6, D-10, D-33).

D-6 says a target is listed only once five artifacts exist — prior art, library coverage,
provenance, attack routes and a root witness — and that intake is *curated*: a person decides,
and the tooling refuses what is under-documented rather than deciding for them. So this module
is mostly refusals, and every one of them happens before a byte is written (C7).

Three commands live here, and they are deliberately three rather than one:

``intake new``
    Everything that makes a target exist: the record, the ``gate-spec.json`` pinning the graph's
    Mathlib (D-7), the root node and the definitions it is stated over, a ``mechanical-only``
    certificate for each of them, and a ``listed`` declaration. Admission runs on the root and on
    each definition before any of it is kept.
``intake post``
    The D-10 posting. A target that has not been posted upstream is not claimable, and posting is
    a thing a person does in the world; the record follows it.
``intake activate``
    D-33's flip to ``active``. It refuses while the target would still not be claimable, and names
    the condition that is missing — which is the whole point of deriving claimability rather than
    declaring it.

**Claimability is derived, never written** (R4). Its three inputs each have exactly one home: the
status comes from the target's ``status/`` records (D-33), the grade from its fidelity
certificates (R3), and the posting from this record. A target with no ``target.yaml`` at all is a
pre-F11 target and keeps F03's rule (Q4, Q5), so the tutorial graph is untouched.
"""

from __future__ import annotations

import logging
import shutil
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from opn_gate import fidelity, layout, schemas

log = logging.getLogger(__name__)

SCHEMA = "target/v1"
TARGET_FILE = "target.yaml"
TARGET_STATUS_SCHEMA = "target-status/v2"
GATE_SPEC_SCHEMA = "gate-spec/v1"
LICENCE_NONE = "none-stated"
LISTED = "listed"
ACTIVE = "active"
DORMANT = "dormant"
#: D-33's statuses under which a node may be claimed (R4). A dormancy declaration refuses no
#: claim — it is a signal to the curator, not a lock on the target.
CLAIMING_STATUSES: tuple[str, ...] = (ACTIVE, DORMANT)

#: D-6's Stage 0 exclusions. Not a judgment about the mathematics: these are the domains where a
#: statement's fidelity cannot be screened by anyone the network can currently reach.
EXCLUDED_DOMAINS: frozenset[str] = frozenset(
    {"algebraic-geometry", "algebraic-number-theory", "differential-geometry", "pde"}
)


class IntakeError(ValueError):
    """The target cannot be taken in as described. Raised before anything is written."""


@dataclass(frozen=True)
class SubjectCheck:
    """One admission result, for the root node or for one definition file."""

    subject: str
    ok: bool
    detail: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {"subject": self.subject, "ok": self.ok, "detail": self.detail}


#: The seam R2's admission runs behind: ``(path, subject) -> SubjectCheck``, where ``path`` is the
#: root's node directory or one ``defs/*.lean`` file. The CLI wires it to ``opn_gate.admit`` and
#: the toolchain; the fast tier hands in a fake, because admission needs Lean and intake's
#: refusals do not (conventions §2).
Checker = Callable[[Path, str], SubjectCheck]


# --- the record ----------------------------------------------------------------------------


def target_dir(graph_root: Path, target_id: str) -> Path:
    return graph_root / "targets" / target_id


def record_path(target_directory: Path) -> Path:
    return target_directory / TARGET_FILE


def curator_of(target_directory: Path) -> str | None:
    """The target's curator (D-21: they earn no proof credit on it), or ``None`` for a target
    that predates F11 and so has no curator on record."""
    doc = load_doc(target_directory)
    return None if doc is None else str(doc["curator"])


def load_doc(target_directory: Path) -> dict[str, Any] | None:
    """The target's ``target.yaml``, or ``None`` for a target that predates F11."""
    path = record_path(target_directory)
    if not path.is_file():
        return None
    return schemas.load_yaml(path, SCHEMA)


def write_doc(target_directory: Path, doc: dict[str, Any]) -> Path:
    path = record_path(target_directory)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(schemas.validate(doc, SCHEMA), sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return path


# --- R2's refusals -------------------------------------------------------------------------


def check_artifacts(doc: dict[str, Any]) -> None:
    """D-6's artifacts, as content rather than as keys.

    The schema already requires the keys; what it cannot require is that they say anything. An
    empty prior-art summary is exactly the under-documented target D-6 exists to keep off the
    list. Attack routes are the one artifact allowed to be empty (R2): "we have no idea how to
    attack this" is an honest and common answer, and pretending otherwise would invite fiction.
    """
    missing: list[str] = []
    if not str(doc["prior_art"].get("summary", "")).strip():
        missing.append("prior art (prior_art.summary is empty)")
    coverage = doc["library_coverage"]
    if "mathlib_sha" not in coverage or "missing_prerequisites" not in coverage:
        missing.append("library coverage (mathlib_sha and missing_prerequisites)")
    provenance = doc["provenance"]
    if not str(provenance.get("author", "")).strip():
        missing.append("provenance (provenance.author is empty)")
    if missing:
        msg = "D-6 needs every artifact before a target is listed; missing: " + "; ".join(missing)
        raise IntakeError(msg)


def check_domains(doc: dict[str, Any]) -> None:
    """R2: no target in one of D-6's four excluded domains is taken in at Stage 0."""
    excluded = sorted(set(doc["domains"]) & EXCLUDED_DOMAINS)
    if excluded:
        msg = (
            f"{', '.join(excluded)} is outside Stage 0 intake (D-6 excludes "
            f"{', '.join(sorted(EXCLUDED_DOMAINS))})"
        )
        raise IntakeError(msg)


def check_quotation(doc: dict[str, Any]) -> None:
    """R10, at the record rather than at the page.

    A source that publishes no licence has not given anyone permission to republish its wording,
    and the graph is published. So the informal statement of such a source is simply not stored:
    the network's own paraphrase stands in its place, and the page renders the citation and the
    link. Enforcing it here means the site cannot leak what the graph does not hold.
    """
    unlicensed = [s for s in doc["sources"] if str(s["licence"]) == LICENCE_NONE]
    if unlicensed and doc.get("informal") is not None:
        where = ", ".join(str(s["url"]) for s in unlicensed)
        msg = (
            f"{where} states no licence, so its informal statement may not be reproduced (R10): "
            "leave `informal` null and give a `paraphrase`"
        )
        raise IntakeError(msg)
    if doc.get("informal") is None and not str(doc.get("paraphrase") or "").strip():
        msg = "with no informal statement on record the target needs a one-line `paraphrase` (R10)"
        raise IntakeError(msg)


def check_witness(root_dir: Path) -> None:
    """D-6's fifth artifact: the root has a witness, and it is not the empty slot (D-4 step 7)."""
    from opn_gate import graph as graphmod  # noqa: PLC0415 — only this check needs the loader

    witness = root_dir / "Witness.lean"
    if not witness.is_file():
        msg = "the root has no Witness.lean; D-6 wants a root witness before it is listed"
        raise IntakeError(msg)
    if graphmod.witness_is_stub(root_dir):
        msg = (
            f"{witness.name} is still the unfilled slot; a listed target's root carries a real "
            "witness (D-6, D-4 step 7)"
        )
        raise IntakeError(msg)


def check(doc: dict[str, Any], root_dir: Path) -> None:
    """Every refusal R2 names, in the order a curator would hit them."""
    check_artifacts(doc)
    check_domains(doc)
    check_quotation(doc)
    check_witness(root_dir)


# --- R4: claimability, derived -----------------------------------------------------------


def claimability(
    doc: dict[str, Any] | None, *, status: str, grade: str | None
) -> tuple[bool, tuple[str, ...]]:
    """R4: ``(claimable, reasons)``. The reasons are empty exactly when it is claimable.

    ``doc`` is ``None`` for a pre-F11 target, which this does not decide for: the caller keeps
    F03's rule there.
    """
    if doc is None:
        msg = "claimability is derived from a target record; this target has none"
        raise IntakeError(msg)
    reasons: list[str] = []
    if status not in CLAIMING_STATUSES:
        reasons.append(f"status-{status}")
    if not fidelity.meets(grade):
        reasons.append(f"grade-below-{fidelity.CLAIMABLE_GRADE}")
    if doc.get("posting") is None:
        reasons.append("no-posting")
    return not reasons, tuple(reasons)


def explain(reason: str) -> str:
    """One reason, in the words the Targets page uses (R10)."""
    if reason.startswith("status-"):
        return f"the target's D-33 status is {reason.removeprefix('status-')}"
    if reason.startswith("grade-below-"):
        return f"its fidelity grade is below {reason.removeprefix('grade-below-')} (D-9)"
    if reason == "no-posting":
        return "it has not been posted upstream (D-10)"
    return reason


# --- intake new (R2) -----------------------------------------------------------------------


@dataclass(frozen=True)
class Intake:
    target_id: str
    root: str
    written: tuple[str, ...]
    checks: tuple[SubjectCheck, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "target": self.target_id,
            "root": self.root,
            "written": list(self.written),
            "admission": [c.as_dict() for c in self.checks],
        }


def status_doc(status: str, cause: str, *, author: str, date: str) -> dict[str, Any]:
    doc: dict[str, Any] = {
        "schema": TARGET_STATUS_SCHEMA,
        "status": status,
        "cause": cause,
        "author": author,
        "date": date[:10],
    }
    return schemas.validate(doc, TARGET_STATUS_SCHEMA)


def spec_for(
    template: dict[str, Any], *, target_id: str, mathlib_sha: str | None
) -> dict[str, Any]:
    """R2: the new target's ``gate-spec.json`` — the template's, with its own id and Mathlib pin.

    The rest is taken rather than invented: the axiom allowlist, the hazard checkers and the
    step-3 caps are properties of the *gate* the graph pins (D-35), and a target that quietly
    ran under a different allowlist would be a second trust base.
    """
    spec = dict(template)
    spec["graph_id"] = target_id
    spec["mathlib_sha"] = mathlib_sha
    return schemas.validate(spec, GATE_SPEC_SCHEMA)


def new(  # noqa: PLR0913 — one argument per input the target is built from
    graph_root: Path,
    target_id: str,
    *,
    doc: dict[str, Any],
    root_dir: Path,
    spec_template: dict[str, Any],
    defs_dir: Path | None = None,
    checker: Checker,
    author: str,
    date: str,
) -> Intake:
    """R2: take the target in, or leave the graph exactly as it was.

    Admission runs on the scaffolded tree rather than on the inputs, because that is the tree the
    gate will see — the F08 lesson that a check reading a file from outside the sandbox's mounts
    passes every laptop tier. The tree is therefore written first and removed whole on any
    failure, which is safe precisely because the target directory is refused if it already
    exists: nothing that was there before can be inside it.
    """
    if str(doc["id"]) != target_id:
        msg = f"the record is for target {doc['id']!r}, not {target_id!r}"
        raise IntakeError(msg)
    destination = target_dir(graph_root, target_id)
    if destination.exists():
        msg = f"target {target_id!r} already exists at {destination}"
        raise IntakeError(msg)
    if not root_dir.is_dir():
        msg = f"--root {root_dir} is not a directory"
        raise IntakeError(msg)
    check(doc, root_dir)
    mathlib_sha = doc["library_coverage"]["mathlib_sha"]
    spec = spec_for(spec_template, target_id=target_id, mathlib_sha=mathlib_sha)
    root_id = root_dir.name
    curator_author = str(doc["provenance"]["author"])

    written: list[str] = []
    try:
        destination.mkdir(parents=True)
        layout.gate_spec_path(graph_root, target_id).write_bytes(schemas.canonical_json(spec))
        write_doc(destination, doc)
        shutil.copytree(root_dir, destination / "nodes" / root_id)
        if defs_dir is not None:
            shutil.copytree(defs_dir, destination / "defs")
        else:
            (destination / "defs").mkdir()
        checks = _admit_all(destination, root_id, checker)
        failed = [c for c in checks if not c.ok]
        if failed:
            names = "; ".join(f"{c.subject}: {c.detail}" for c in failed)
            msg = f"admission refused {target_id!r}: {names}"
            raise IntakeError(msg)
        for subject in fidelity.subjects_of(destination):
            fidelity.attest(
                destination,
                subject,
                fidelity.DEFAULT_GRADE,
                attestor=author,
                subject_author=curator_author,
                date=date[:10],
                evidence=(
                    f"admitted at intake: {subject} elaborates and passes F08's mechanical "
                    "admission. No human has read it against the informal statement, which is "
                    "what D-9's first rung says."
                ),
            )
        (destination / "status").mkdir(exist_ok=True)
        _write_status(
            destination,
            status_doc(
                LISTED,
                f"taken in by {author} (D-6 intake); not claimable until a non-author signs the "
                "statement and the target is posted upstream (D-9, D-10)",
                author=author,
                date=date,
            ),
            author=author,
            date=date,
        )
    except Exception:
        shutil.rmtree(destination, ignore_errors=True)
        raise
    written = sorted(
        p.resolve().relative_to(graph_root.resolve()).as_posix()
        for p in destination.rglob("*")
        if p.is_file()
    )
    log.info("intake: %s listed with root %s", target_id, root_id)
    return Intake(target_id, root_id, tuple(written), checks)


def _admit_all(destination: Path, root_id: str, checker: Checker) -> tuple[SubjectCheck, ...]:
    """R2: admission on the root node, then on each definition file."""
    out = [checker(destination / "nodes" / root_id, fidelity.ROOT_SUBJECT)]
    defs = destination / fidelity.DEFS_DIR
    if defs.is_dir():
        out.extend(
            checker(path, path.stem)
            for path in sorted(defs.iterdir())
            if path.is_file() and path.suffix == ".lean"
        )
    return tuple(out)


def _write_status(destination: Path, doc: dict[str, Any], *, author: str, date: str) -> Path:
    stamp = date.replace("-", "").replace(":", "")
    path = destination / "status" / f"{stamp}-{author}.yaml"
    if path.exists():
        msg = f"{path.name} already exists; status records are append-only"
        raise IntakeError(msg)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return path


# --- intake post and activate (R5) ---------------------------------------------------------


def post(graph_root: Path, target_id: str, *, venue: str, url: str, date: str) -> tuple[str, ...]:
    """R5: record the D-10 posting. Refused when one is already on record — a posting is a fact
    about the world, and a second one would silently replace the first."""
    destination = target_dir(graph_root, target_id)
    doc = load_doc(destination)
    if doc is None:
        msg = f"target {target_id!r} has no {TARGET_FILE}; only a curated target can be posted"
        raise IntakeError(msg)
    if doc.get("posting") is not None:
        existing = doc["posting"]
        msg = (
            f"{target_id!r} is already posted at {existing['url']} ({existing['date']}); "
            "a posting is recorded once (D-10)"
        )
        raise IntakeError(msg)
    doc["posting"] = {"venue": venue, "url": url, "date": date[:10]}
    path = write_doc(destination, doc)
    return (path.resolve().relative_to(graph_root.resolve()).as_posix(),)


def activate(
    graph_root: Path, target_id: str, *, author: str, date: str, status: str | None = None
) -> tuple[str, ...]:
    """R5: flip the target to ``active``, or refuse naming what is still missing.

    The refusal is the useful half. Activation is the moment a curator says "this is open for
    work", and D-6's whole point is that it cannot be said before the statement has been screened
    and the problem posted — so the command derives claimability and reads the reasons back.
    """
    destination = target_dir(graph_root, target_id)
    doc = load_doc(destination)
    if doc is None:
        msg = f"target {target_id!r} has no {TARGET_FILE}; only a curated target is activated"
        raise IntakeError(msg)
    grade = fidelity.target_grade(destination)
    claimable, reasons = claimability(doc, status=ACTIVE, grade=grade)
    if not claimable:
        msg = "cannot activate " + target_id + ": " + "; ".join(explain(r) for r in reasons)
        raise IntakeError(msg)
    path = _write_status(
        destination,
        status_doc(
            status or ACTIVE,
            f"activated by {author}: grade {grade} and a D-10 posting are on record (D-6)",
            author=author,
            date=date,
        ),
        author=author,
        date=date,
    )
    return (path.resolve().relative_to(graph_root.resolve()).as_posix(),)
