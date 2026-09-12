"""The statement-QA record (F12-R1, R2, R5, R9, R15; D-9 v3.12).

F11 gives a target a fidelity grade and a place to keep certificates; it checks nothing. This
module is the record of the checking: one ``qa/v1`` file per run of D-9 v3.12's mechanizable
pass over one subject — the root statement or one definition — at ``targets/<id>/qa/<subject>-
<n>.yaml``, with the kernel-checked exhibits a run produces under ``targets/<id>/qa/exhibits/``.

Three rules are enforced here rather than trusted, because the record is what a grade rests on:

- **Two kinds, never confused** (R2). A check is ``exhibit`` (a kernel fact: a compile, a
  screen's outcome, a proved equivalence) or ``brief`` (a judgement: a review brief, a
  back-translation). Only the first kind counts toward a complete pass; a brief alone raises
  nothing, which is the whole of what keeps a 90%-accurate judge from becoming an authority.
- **An exhibit is trusted by content, never by path** (R15, C9). Every exhibit row that names
  a file carries the file's SHA-256, and the writer and every reader refuse a row whose file is
  missing, whose hash differs, or whose text uses ``sorry`` — each with its own diagnostic —
  and never count it. The ``sorry`` check is a token match (``layout.mentions_sorry``) and is
  not the enforcement; the kernel replay before a grade counts an exhibit is (F12-T4).
- **Staleness is derived, not written** (R5, F12-Q9). A record pins the statement hash and the
  toolchain and Mathlib it ran under; a record for any other hash or pin is stale, so a pin move
  or a D-8 revision makes every record for the subject count for nothing until the screens
  re-run. Nothing edits a record to say so — a stale flag with a writable home would disagree
  with the pins.

What a subject's fresh records yield is a *pass state*: the latest verdict per check, the
checks D-9's floor still lacks, and the positive screens nobody has routed (R4). ``require_
complete`` is the refusal the grade gate uses (R9); ``pass_state`` is what the products publish
(R14).
"""

from __future__ import annotations

import logging
import re
import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import yaml

from opn_gate import fidelity, layout, schemas
from opn_gate import graph as graphmod
from opn_gate.diagnostic import Diagnostic
from opn_gate.steps.base import RunContext
from opn_gate.toolchain import ResolvedToolchain, ToolchainMissingError

log = logging.getLogger(__name__)

SCHEMA = "qa/v1"
QA_DIR = "qa"
EXHIBITS_DIR = "exhibits"
SUFFIXES: tuple[str, ...] = (".yaml", ".yml")

Check = Literal[
    "compile",
    "screen-statement",
    "screen-negation",
    "screen-false",
    "screen-consequence",
    "brief",
    "backtranslation",
    "equivalence",
]
Kind = Literal["exhibit", "brief"]
Verdict = Literal["pass", "fail", "inconclusive"]

#: D-9 v3.12's ordered pass, cheapest first.
CHECKS: tuple[Check, ...] = (
    "compile",
    "screen-statement",
    "screen-negation",
    "screen-false",
    "screen-consequence",
    "brief",
    "backtranslation",
    "equivalence",
)
#: Layer 2: the soundness screens. A ``fail`` here is a *finding* with an exhibit (R3, R4).
SCREENS: tuple[Check, ...] = (
    "screen-statement",
    "screen-negation",
    "screen-false",
    "screen-consequence",
)
#: R2: which layer each check belongs to. Layers 1, 2 and 4 are exhibits; layer 3 is a brief.
KIND_OF: dict[Check, Kind] = {
    "compile": "exhibit",
    "screen-statement": "exhibit",
    "screen-negation": "exhibit",
    "screen-false": "exhibit",
    "screen-consequence": "exhibit",
    "brief": "brief",
    "backtranslation": "brief",
    "equivalence": "exhibit",
}
#: R9: what "the pass complete" means for the root — every layer but the bonus one (F12-Q3:
#: equivalence needs a second formalization and is never part of the floor).
FLOOR_ROOT: tuple[Check, ...] = ("compile", *SCREENS, "brief", "backtranslation")
#: A definition is not a proposition: it has nothing to negate and no hypotheses to close, so
#: its pass is the compile, the brief and the back-translation (F12-Q10).
FLOOR_DEFINITION: tuple[Check, ...] = ("compile", "brief", "backtranslation")

CODE_MISSING = "exhibit-missing"
CODE_HASH = "exhibit-hash-mismatch"
CODE_SORRY = "exhibit-sorry"
#: The diagnostics a row can be refused with, in the order they are checked (R15).
REFUSAL_CODES: tuple[str, ...] = (CODE_MISSING, CODE_HASH, CODE_SORRY)


class QaError(ValueError):
    """The record cannot be written or read as evidence. Nothing is written.

    ``code`` names the rule (one of ``REFUSAL_CODES`` for an exhibit row; ``pass-incomplete``
    for the grade gate's refusal; ``record`` for anything about the record's shape).
    """

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


# --- rows and records ----------------------------------------------------------------------------


@dataclass(frozen=True)
class Row:
    """One check result, as the record stores it."""

    check: Check
    kind: Kind
    tool: str
    tool_version: str
    model: str | None
    model_version: str | None
    verdict: Verdict
    exhibit: str | None  # relative to the graph root
    exhibit_sha256: str | None
    timestamp: str
    elapsed_s: float | None = None
    budget_s: float | None = None
    note: str | None = None

    @property
    def is_finding(self) -> bool:
        """A screen that proved its target: the finding D-9 routes to a person (R4)."""
        return self.check in SCREENS and self.verdict == "fail"

    def as_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "check": self.check,
            "kind": self.kind,
            "tool": self.tool,
            "tool_version": self.tool_version,
            "model": self.model,
            "model_version": self.model_version,
            "verdict": self.verdict,
            "exhibit": self.exhibit,
            "exhibit_sha256": self.exhibit_sha256,
            "timestamp": self.timestamp,
        }
        if self.elapsed_s is not None:
            out["elapsed_s"] = self.elapsed_s
        if self.budget_s is not None:
            out["budget_s"] = self.budget_s
        if self.note is not None:
            out["note"] = self.note
        return out

    @classmethod
    def from_dict(cls, doc: dict[str, Any]) -> Row:
        return cls(
            check=doc["check"],
            kind=doc["kind"],
            tool=str(doc["tool"]),
            tool_version=str(doc["tool_version"]),
            model=_optional_str(doc.get("model")),
            model_version=_optional_str(doc.get("model_version")),
            verdict=doc["verdict"],
            exhibit=_optional_str(doc.get("exhibit")),
            exhibit_sha256=_optional_str(doc.get("exhibit_sha256")),
            timestamp=str(doc["timestamp"]),
            elapsed_s=_optional_float(doc.get("elapsed_s")),
            budget_s=_optional_float(doc.get("budget_s")),
            note=_optional_str(doc.get("note")),
        )


def _optional_str(value: object) -> str | None:
    return str(value) if isinstance(value, str) and value else None


def _optional_float(value: object) -> float | None:
    return float(value) if isinstance(value, int | float) and not isinstance(value, bool) else None


def row(  # noqa: PLR0913 — one argument per fact the row records
    check: Check,
    verdict: Verdict,
    *,
    tool: str,
    tool_version: str,
    timestamp: str,
    model: str | None = None,
    model_version: str | None = None,
    exhibit: str | None = None,
    exhibit_sha256: str | None = None,
    elapsed_s: float | None = None,
    budget_s: float | None = None,
    note: str | None = None,
) -> Row:
    """A row whose kind is the check's, with the coherence rules the schema cannot state.

    A screen that found something has an exhibit and one that found nothing has none; an
    exhibit path always comes with its hash (R15); a brief that names no model is a brief
    nobody ran (R6, R7).
    """
    if check not in KIND_OF:
        msg = f"unknown check {check!r}; D-9's pass is {', '.join(CHECKS)}"
        raise QaError("record", msg)
    kind = KIND_OF[check]
    if (exhibit is None) != (exhibit_sha256 is None):
        msg = f"{check}: an exhibit path and its SHA-256 go together (R15)"
        raise QaError("record", msg)
    if check in SCREENS and verdict == "fail" and exhibit is None:
        msg = f"{check}: a screen that succeeded is a finding, and a finding carries its exhibit"
        raise QaError("record", msg)
    if check in SCREENS and verdict == "pass" and exhibit is not None:
        msg = f"{check}: a screen that found nothing produced nothing; {exhibit} is not its"
        raise QaError("record", msg)
    if kind == "brief" and verdict == "pass" and model is None:
        msg = f"{check}: a {kind} row records the model that produced it (R6, R7)"
        raise QaError("record", msg)
    return Row(
        check=check,
        kind=kind,
        tool=tool,
        tool_version=tool_version,
        model=model,
        model_version=model_version,
        verdict=verdict,
        exhibit=exhibit,
        exhibit_sha256=exhibit_sha256,
        timestamp=timestamp,
        elapsed_s=elapsed_s,
        budget_s=budget_s,
        note=note,
    )


@dataclass(frozen=True)
class Record:
    """One ``qa/v1`` file, with where it came from."""

    subject: str
    statement_hash: str
    lean_toolchain: str
    mathlib_sha: str | None
    date: str
    produced_by: str
    checks: tuple[Row, ...]
    path: Path | None = None

    @property
    def name(self) -> str:
        return self.path.name if self.path is not None else "<unwritten>"

    def stale(self, statement_hash: str, spec: dict[str, Any]) -> bool:
        """R5: the record is for another statement, or ran under another pin."""
        return (
            self.statement_hash != statement_hash
            or self.lean_toolchain != str(spec["lean_toolchain"])
            or self.mathlib_sha != _optional_str(spec.get("mathlib_sha"))
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "subject": self.subject,
            "statement_hash": self.statement_hash,
            "lean_toolchain": self.lean_toolchain,
            "mathlib_sha": self.mathlib_sha,
            "date": self.date,
            "produced_by": self.produced_by,
            "checks": [r.as_dict() for r in self.checks],
        }


# --- where things are ----------------------------------------------------------------------------


def qa_dir(target_dir: Path) -> Path:
    return target_dir / QA_DIR


def exhibits_dir(target_dir: Path) -> Path:
    return qa_dir(target_dir) / EXHIBITS_DIR


def graph_root_of(target_dir: Path) -> Path:
    """``targets/<id>`` sits two levels under the graph root (D-35's layout)."""
    return target_dir.resolve().parents[1]


def relative(target_dir: Path, path: Path) -> str:
    return path.resolve().relative_to(graph_root_of(target_dir)).as_posix()


def spec_of(target_dir: Path) -> dict[str, Any]:
    return schemas.load_json(target_dir / "gate-spec.json", "gate-spec/v1")


def root_node(target_dir: Path) -> str:
    """The target's root node id, derived the way the products derive it (F03-Q5, F08-Q19)."""
    graph_root = graph_root_of(target_dir)
    return graphmod.load_target(graph_root, target_dir.name).root


def subject_hash(target_dir: Path, subject: str) -> str:
    """What the record pins: the root's statement hash, or a definition file's SHA-256.

    Both are content hashes of the one file the subject *is* (D-3): a changed statement or a
    changed definition is a different subject, and every record for the old one is stale (R5).
    """
    if subject == fidelity.ROOT_SUBJECT:
        node_dir = layout.graph_nodes_dir(graph_root_of(target_dir), target_dir.name)
        loaded = layout.load_node(node_dir / root_node(target_dir), target_dir.name)
        if isinstance(loaded, list):
            msg = f"the root of {target_dir.name} does not load: {loaded[0].message}"
            raise QaError("record", msg)
        return loaded.statement.statement_hash
    definition = target_dir / fidelity.DEFS_DIR / f"{subject}.lean"
    if subject not in fidelity.definitions(target_dir) or not definition.is_file():
        known = ", ".join(fidelity.subjects_of(target_dir))
        msg = f"{subject!r} is not a QA subject of {target_dir.name}; the subjects are {known}"
        raise QaError("record", msg)
    return schemas.content_hash(definition.read_bytes())


def floor_for(subject: str) -> tuple[Check, ...]:
    return FLOOR_ROOT if subject == fidelity.ROOT_SUBJECT else FLOOR_DEFINITION


# --- the exhibit store (R15) ----------------------------------------------------------------------


def check_exhibit(graph_root: Path, row_: Row) -> Diagnostic | None:
    """R15: the one place a row's file is judged. ``None`` when the row may count.

    Three refusals in order — missing, altered, ``sorry`` — each named, because a reader that
    said only "refused" would leave a curator guessing which of the three forgeries it saw.
    A ``brief`` row's file is not evidence for anything and is not checked here.
    """
    if row_.kind != "exhibit" or row_.exhibit is None:
        return None
    path = graph_root / row_.exhibit
    if not path.is_file():
        return Diagnostic(
            CODE_MISSING,
            f"{row_.check}: exhibit {row_.exhibit} is not in the graph; a row is evidence only "
            "with its file (R15)",
            {"check": row_.check, "exhibit": row_.exhibit},
        )
    data = path.read_bytes()
    actual = schemas.content_hash(data)
    if actual != row_.exhibit_sha256:
        return Diagnostic(
            CODE_HASH,
            f"{row_.check}: exhibit {row_.exhibit} does not hash to what the row recorded; an "
            "exhibit is trusted by content, never by path (R15, C9)",
            {
                "check": row_.check,
                "exhibit": row_.exhibit,
                "recorded": row_.exhibit_sha256,
                "actual": actual,
            },
        )
    if layout.mentions_sorry(data.decode("utf-8", errors="replace")):
        return Diagnostic(
            CODE_SORRY,
            f"{row_.check}: exhibit {row_.exhibit} uses sorry, so nothing in it was proved (R15)",
            {"check": row_.check, "exhibit": row_.exhibit},
        )
    return None


def store_exhibit(target_dir: Path, name: str, text: str) -> tuple[str, str]:
    """Write an exhibit under ``qa/exhibits/`` and answer ``(path relative to the graph root,
    sha256)``. Append-only: a name already taken is a refusal, and a text that uses ``sorry`` is
    refused before it is stored — the store never holds a file a row could not cite."""
    if layout.mentions_sorry(text):
        msg = f"exhibit {name} uses sorry; a kernel-checked exhibit proves what it says (R15)"
        raise QaError(CODE_SORRY, msg)
    path = exhibits_dir(target_dir) / name
    if path.exists():
        msg = f"{path} already exists; exhibits are append-only (D-34, C9)"
        raise QaError("record", msg)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = text.encode("utf-8")
    path.write_bytes(data)
    return relative(target_dir, path), schemas.content_hash(data)


def exhibit_name(subject: str, check: str, target_dir: Path, suffix: str = ".lean") -> str:
    """``<subject>-<check>-<n><suffix>`` for the next free ``n``."""
    directory = exhibits_dir(target_dir)
    taken = {p.name for p in directory.iterdir()} if directory.is_dir() else set()
    n = 1
    while f"{subject}-{check}-{n}{suffix}" in taken:
        n += 1
    return f"{subject}-{check}-{n}{suffix}"


# --- writing and reading records ----------------------------------------------------------------


def record_path(target_dir: Path, subject: str) -> Path:
    """``qa/<subject>-<n>.yaml`` for the next free ``n`` — one file per run, never a rewrite."""
    directory = qa_dir(target_dir)
    taken = {p.name for p in directory.iterdir()} if directory.is_dir() else set()
    n = 1
    while f"{subject}-{n}.yaml" in taken:
        n += 1
    return directory / f"{subject}-{n}.yaml"


def write(  # noqa: PLR0913 — one argument per fact the record pins
    target_dir: Path,
    subject: str,
    rows: list[Row] | tuple[Row, ...],
    *,
    date: str,
    produced_by: str,
    spec: dict[str, Any] | None = None,
    statement_hash: str | None = None,
) -> Path:
    """R1: append one run's record, refusing before anything is written.

    Every exhibit row is checked against its file first (R15): the writer is the first reader,
    and a row it would not count is a row it does not write.
    """
    if not rows:
        raise QaError("record", "a QA record holds at least one check")
    if subject not in fidelity.subjects_of(target_dir):
        known = ", ".join(fidelity.subjects_of(target_dir))
        msg = f"{subject!r} is not a QA subject of {target_dir.name}; the subjects are {known}"
        raise QaError("record", msg)
    graph_root = graph_root_of(target_dir)
    for row_ in rows:
        problem = check_exhibit(graph_root, row_)
        if problem is not None:
            raise QaError(problem.code, problem.message)
    spec = spec if spec is not None else spec_of(target_dir)
    record = Record(
        subject=subject,
        statement_hash=statement_hash or subject_hash(target_dir, subject),
        lean_toolchain=str(spec["lean_toolchain"]),
        mathlib_sha=_optional_str(spec.get("mathlib_sha")),
        date=date,
        produced_by=produced_by,
        checks=tuple(rows),
    )
    doc = schemas.validate(record.as_dict(), SCHEMA)
    path = record_path(target_dir, subject)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True), encoding="utf-8")
    log.info("qa: %s/%s recorded %d checks in %s", target_dir.name, subject, len(rows), path.name)
    return path


def load(target_dir: Path) -> dict[str, list[Record]]:
    """Every record, by subject, oldest first by ``(date, file name)``.

    A record that does not validate raises, as a fidelity certificate does (F11-R3): the record
    gates a grade, and skipping a broken one would let a grade rest on nothing.
    """
    directory = qa_dir(target_dir)
    out: dict[str, list[Record]] = {}
    if not directory.is_dir():
        return out
    for path in sorted(p for p in directory.iterdir() if p.is_file() and p.suffix in SUFFIXES):
        doc = schemas.load_yaml(path, SCHEMA)
        record = Record(
            subject=str(doc["subject"]),
            statement_hash=str(doc["statement_hash"]),
            lean_toolchain=str(doc["lean_toolchain"]),
            mathlib_sha=_optional_str(doc.get("mathlib_sha")),
            date=str(doc["date"]),
            produced_by=str(doc["produced_by"]),
            checks=tuple(Row.from_dict(r) for r in doc["checks"]),
            path=path,
        )
        out.setdefault(record.subject, []).append(record)
    for records in out.values():
        records.sort(key=lambda r: (r.date, r.name))
    return out


# --- the pass state (R9, R14) --------------------------------------------------------------------


@dataclass(frozen=True)
class Finding:
    """A positive screen: a kernel-checked exhibit that D-9 routes to a person (R4)."""

    check: Check
    exhibit: str
    exhibit_sha256: str
    record: str  # the file name of the record that carries it
    routed: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "check": self.check,
            "exhibit": self.exhibit,
            "exhibit_sha256": self.exhibit_sha256,
            "record": self.record,
            "routed": self.routed,
        }


#: How the pass state learns whether a finding has been routed (R4): by the defect claims a
#: curator appended (``opn_gate.qa.routed_by_claims``, F12-T2). Nothing routed is the default,
#: which is the safe direction: an unrouted finding holds the grade.
Routed = Callable[[Finding], bool]


@dataclass(frozen=True)
class PassState:
    """What a subject's fresh records say, in the shape the grade gate and the products read."""

    subject: str
    statement_hash: str
    floor: tuple[Check, ...]
    checks: dict[str, str | None]  # every check -> latest fresh verdict, or None
    fresh_records: int
    stale_records: int
    refused: tuple[Diagnostic, ...] = ()  # rows that failed R15 and were not counted
    findings: tuple[Finding, ...] = ()
    exhibits: tuple[Row, ...] = ()  # the accepted exhibit rows that name a file (R2, T4 replays)
    briefs: tuple[Row, ...] = ()  # the accepted brief rows that name a file

    @property
    def missing(self) -> tuple[Check, ...]:
        """The floor checks not yet passed for the current statement under the current pin."""
        return tuple(c for c in self.floor if self.checks.get(c) != "pass")

    @property
    def unrouted(self) -> tuple[Finding, ...]:
        return tuple(f for f in self.findings if not f.routed)

    @property
    def routed_findings(self) -> tuple[Finding, ...]:
        return tuple(f for f in self.findings if f.routed)

    @property
    def complete(self) -> bool:
        """R9: every floor check passed and no positive screen awaits a person."""
        return not self.missing and not self.unrouted

    @property
    def stale(self) -> bool:
        """Records exist for this subject, and none of them is for the statement as it stands."""
        return self.fresh_records == 0 and self.stale_records > 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "subject": self.subject,
            "statement_hash": self.statement_hash,
            "checks": {c: self.checks.get(c) for c in CHECKS},
            "complete": self.complete,
            "missing": list(self.missing),
            "stale": self.stale,
            "fresh_records": self.fresh_records,
            "stale_records": self.stale_records,
            "findings": [f.as_dict() for f in self.findings],
            "unrouted_findings": len(self.unrouted),
            "refused": [d.as_dict() for d in self.refused],
        }


def pass_state(
    target_dir: Path,
    subject: str,
    *,
    spec: dict[str, Any] | None = None,
    routed: Routed | None = None,
    statement_hash: str | None = None,
) -> PassState:
    """R9, R14: the latest fresh verdict per check, with every refused row named and not counted.

    "Latest" is by record order then row order, so a re-run supersedes an earlier run of the
    same check and an earlier finding stays a finding until a fresh run passes the screen. A
    finding is a fact about a statement, and a clean re-run of the same screen on the same
    statement means the budget or the library moved, not that the finding was wrong — so a
    finding is only ever cleared by routing (R4), never by a later ``pass``.
    """
    spec = spec if spec is not None else spec_of(target_dir)
    current = statement_hash or subject_hash(target_dir, subject)
    graph_root = graph_root_of(target_dir)
    records = load(target_dir).get(subject, [])
    fresh = [r for r in records if not r.stale(current, spec)]
    checks: dict[str, str | None] = dict.fromkeys(CHECKS)
    refused: list[Diagnostic] = []
    findings: list[Finding] = []
    exhibits: list[Row] = []
    briefs: list[Row] = []
    for record in fresh:
        for row_ in record.checks:
            problem = check_exhibit(graph_root, row_)
            if problem is not None:
                refused.append(
                    Diagnostic(
                        problem.code, problem.message, {**problem.details, "record": record.name}
                    )
                )
                continue
            checks[row_.check] = row_.verdict
            if row_.is_finding:
                assert row_.exhibit is not None and row_.exhibit_sha256 is not None
                finding = Finding(row_.check, row_.exhibit, row_.exhibit_sha256, record.name)
                findings.append(
                    Finding(
                        finding.check,
                        finding.exhibit,
                        finding.exhibit_sha256,
                        finding.record,
                        routed=bool(routed(finding)) if routed is not None else False,
                    )
                )
            if row_.exhibit is not None:
                (exhibits if row_.kind == "exhibit" else briefs).append(row_)
    return PassState(
        subject=subject,
        statement_hash=current,
        floor=floor_for(subject),
        checks=checks,
        fresh_records=len(fresh),
        stale_records=len(records) - len(fresh),
        refused=tuple(refused),
        findings=tuple(findings),
        exhibits=tuple(exhibits),
        briefs=tuple(briefs),
    )


def require_complete(
    target_dir: Path,
    subject: str,
    *,
    spec: dict[str, Any] | None = None,
    routed: Routed | None = None,
) -> PassState:
    """R9: the pass state, or a refusal naming exactly what is missing — the screens not run, the
    findings nobody has routed, the rows whose exhibits could not be trusted, or the staleness
    that made every record count for nothing (AC1, AC4, AC21-AC23)."""
    state = pass_state(target_dir, subject, spec=spec, routed=routed)
    if state.complete:
        return state
    reasons: list[str] = []
    if state.stale:
        reasons.append(
            f"every QA record for {subject} is stale: the statement or the graph's pin moved "
            "since it ran, so the screens must re-run (R5)"
        )
    if state.missing:
        reasons.append(
            "the pass is not complete for the statement as it stands; not passed: "
            + ", ".join(state.missing)
        )
    if state.unrouted:
        reasons.append(
            "positive screens await a person's routing (R4): "
            + ", ".join(f"{f.check} ({f.exhibit})" for f in state.unrouted)
        )
    if state.refused:
        reasons.append(
            "rows refused and not counted (R15): "
            + "; ".join(f"{d.code}: {d.details.get('exhibit')}" for d in state.refused)
        )
    code = state.refused[0].code if state.refused and not state.missing else "pass-incomplete"
    msg = f"{subject} cannot rise to {fidelity.SIGNED_FROM}: " + "; ".join(reasons)
    raise QaError(code, msg)


# --- the soundness screens (R3, R4; D-9 v3.12 layer 2) --------------------------------------------
#
# Four attempts, each a scratch Lean file that names the statement as a goal or a hypothesis and
# never as a ``sorry`` in a graph file: prove the statement, prove its negation, prove ``False``
# from its hypotheses, and derive each declared consequence. Any success is a *finding*: the
# proof is replayed through the kernel (D-4 step 4) with the axiom check (step 5), stored as an
# exhibit, and filed as a ``screen-finding`` defect claim that names both readings (R4). A
# timeout, an exhausted budget or an error is ``inconclusive`` — never a clean pass (C7).

SCREEN_TOOL = "opn-gate qa screen"
SCREEN_CONTRIBUTOR = "opn-gate-qa"
SCREEN_NAMESPACE = "OpnQa"
CONSEQUENCES_DIR = "consequences"
#: The bounded tactic budget's *shape*: cheap closers first, then a library search. Each attempt
#: also runs under the wall-clock budget (``OPN_QA_ATTEMPT_BUDGET_S``), which is the bound that
#: holds whatever the tactics do. ``aesop`` exists only under Mathlib (D-7).
SCREEN_TACTICS_CORE: tuple[str, ...] = (
    "(intros; simp_all)",
    "(intros; omega)",
    "decide",
    "(intros; exact?)",
)
SCREEN_TACTICS_MATHLIB: tuple[str, ...] = ("(intros; aesop)", "(intros; norm_num)")
SCREEN_HEARTBEATS = 400000
NOTE_BUDGET = "budget-exhausted: the per-subject budget was spent before this attempt started"
NOTE_TIMEOUT = "timed out: the attempt exceeded the per-attempt budget"
NOTE_NO_CONSEQUENCES = "no consequence lemma is declared under qa/consequences/; nothing to derive"

_THEOREM_HEAD_RE = re.compile(r"(?:theorem|lemma)\s+[^\s:({\[⦃]+")
_OPENERS = "({[⦃⟨"
_CLOSERS = ")}]⦄⟩"
_ARROW = "→"
_FORALL = "∀"


@dataclass(frozen=True)
class Signature:
    """A statement's declared shape: its explicit binders and the proposition after the colon."""

    binders: str  # ``(n : Nat) {m : Nat}``, or ``""``
    prop: str

    @property
    def closed(self) -> str:
        """The proposition with the binders folded in: what a hypothesis of it says."""
        return f"{_FORALL} {self.binders}, {self.prop}" if self.binders else self.prop

    @property
    def negation(self) -> str:
        return f"¬ ({self.closed})"

    @property
    def false_form(self) -> str:
        """The proposition with its conclusion replaced by ``False``: provable exactly when the
        hypotheses are contradictory (the vacuity screen). A proposition with no hypotheses
        becomes ``False`` itself, which is an honest attempt rather than a vacuous pass."""
        return conclusion_to_false(self.prop)


def _balanced_end(text: str, start: int) -> int:
    """The index just past the group that opens at ``start``; ``-1`` when it never closes."""
    depth = 0
    for i in range(start, len(text)):
        if text[i] in _OPENERS:
            depth += 1
        elif text[i] in _CLOSERS:
            depth -= 1
            if depth == 0:
                return i + 1
    return -1


def signature_of(statement: layout.Statement) -> Signature | Diagnostic:
    """The binders and the proposition of a D-3 statement, from its text.

    Reads the one shape ``layout.parse_statement`` already admits — ``theorem N binders : P :=
    sorry`` — so what it cannot read is a diagnostic, and the screen records ``inconclusive``
    rather than guessing at a proposition (C7, F12-Q11).
    """
    head = statement.prefix[: -len(":=")] if statement.prefix.endswith(":=") else statement.prefix
    m = _THEOREM_HEAD_RE.search(head)
    if m is None:
        return Diagnostic("statement-shape", "the statement declares no theorem")
    rest = head[m.end() :].strip()
    binders: list[str] = []
    while rest and rest[0] in "({[⦃":
        end = _balanced_end(rest, 0)
        if end == -1:
            return Diagnostic("statement-shape", "a binder group in the statement never closes")
        binders.append(rest[:end])
        rest = rest[end:].lstrip()
    if not rest.startswith(":"):
        return Diagnostic(
            "statement-shape",
            "the statement's signature is not `theorem <name> <binders> : <proposition>`",
            {"after_binders": rest[:40]},
        )
    prop = rest[1:].strip()
    if not prop:
        return Diagnostic("statement-shape", "the statement has an empty proposition")
    return Signature(" ".join(binders), prop)


def _split_top_level(text: str, token: str) -> list[str]:
    """Split ``text`` on ``token`` outside every bracket group."""
    pieces: list[str] = []
    depth = 0
    current = ""
    i = 0
    while i < len(text):
        ch = text[i]
        if ch in _OPENERS:
            depth += 1
        elif ch in _CLOSERS:
            depth -= 1
        if depth == 0 and text.startswith(token, i):
            pieces.append(current)
            current = ""
            i += len(token)
            continue
        current += ch
        i += 1
    pieces.append(current)
    return pieces


def conclusion_to_false(prop: str) -> str:
    """``∀ x, H₁ → H₂ → C`` becomes ``∀ x, H₁ → H₂ → False``; a proposition with no top-level
    hypothesis becomes ``False`` under its binders. Only the *last* top-level arrow is the
    conclusion's; anything inside brackets is left alone."""
    text = prop.strip()
    prefix = ""
    while text.startswith(_FORALL):
        comma = _split_top_level(text, ",")
        if len(comma) < 2:
            break
        prefix += comma[0] + ","
        text = ",".join(comma[1:]).strip()
    arrows = _split_top_level(text, _ARROW)
    hyps = [h.strip() for h in arrows[:-1]]
    body = " → ".join([*hyps, "False"]) if hyps else "False"
    return f"{prefix} {body}".strip() if prefix else body


@dataclass(frozen=True)
class Attempt:
    """One scratch theorem the screen tries to prove."""

    check: Check
    stem: str  # the module and file stem under ``OpnQa/``
    decl: str
    goal: str
    binders: str = ""
    hypothesis: str | None = None  # the subject, introduced as an explicit hypothesis
    note: str | None = None
    extra_imports: tuple[str, ...] = ()


def consequences(target_dir: Path) -> list[tuple[str, layout.Statement]] | Diagnostic:
    """The declared consequence lemmas: ``qa/consequences/<Name>.lean``, each in the statement
    shape (one sorry-bodied theorem), named for its file."""
    directory = qa_dir(target_dir) / CONSEQUENCES_DIR
    if not directory.is_dir():
        return []
    out: list[tuple[str, layout.Statement]] = []
    for path in sorted(p for p in directory.iterdir() if p.is_file() and p.suffix == ".lean"):
        parsed = layout.parse_statement(path.read_text(encoding="utf-8"))
        if isinstance(parsed, Diagnostic):
            return Diagnostic(
                "consequence-shape",
                f"qa/consequences/{path.name}: {parsed.message}",
                {"file": path.name},
            )
        out.append((path.stem, parsed))
    return out


def attempts_for(
    signature: Signature, declared: list[tuple[str, layout.Statement]]
) -> list[Attempt] | Diagnostic:
    """R3's four kinds, in order: the statement, its negation, False from its hypotheses, and
    each declared consequence under the statement as a hypothesis."""
    out = [
        Attempt(
            "screen-statement",
            "ScreenStatement",
            "screen_statement",
            signature.prop,
            binders=signature.binders,
        ),
        Attempt("screen-negation", "ScreenNegation", "screen_negation", signature.negation),
        Attempt(
            "screen-false",
            "ScreenFalse",
            "screen_false",
            signature.false_form,
            binders=signature.binders,
        ),
    ]
    for name, statement in declared:
        shape = signature_of(statement)
        if isinstance(shape, Diagnostic):
            return Diagnostic(shape.code, f"consequence {name}: {shape.message}", shape.details)
        stem = "".join(ch for ch in name if ch.isalnum()) or "Consequence"
        out.append(
            Attempt(
                "screen-consequence",
                f"ScreenConsequence{stem}",
                f"screen_consequence_{stem}",
                shape.closed,
                hypothesis=signature.closed,
                note=f"consequence {name}",
                extra_imports=tuple(
                    m
                    for m in layout.imports_of(statement.text)
                    if layout.module_origin(m)[0] in ("library", "defs")
                ),
            )
        )
    return out


def scratch_source(attempt: Attempt, *, imports: list[str], mathlib: bool) -> str:
    """The scratch file: the statement's own imports, the goal, the bounded tactic script."""
    tactics = [*SCREEN_TACTICS_CORE, *(SCREEN_TACTICS_MATHLIB if mathlib else ())]
    lines = [f"import {m}" for m in imports]
    lines += [
        "",
        f"/-! {SCREEN_TOOL}: {attempt.check}. The subject enters as a goal or an explicit",
        "hypothesis, never as a sorry in a graph file (F12-R3; D-9 v3.12). A proof here is a",
        "finding a person routes (R4): a misformalization (D-8) or a refutation (D-12). -/",
        "",
        f"set_option maxHeartbeats {SCREEN_HEARTBEATS} in",
    ]
    binders = attempt.binders
    if attempt.hypothesis is not None:
        binders = (binders + " " if binders else "") + f"(opn_subject : {attempt.hypothesis})"
    head = f"theorem {SCREEN_NAMESPACE}.{attempt.decl}"
    if binders:
        head += f" {binders}"
    lines.append(f"{head} : {attempt.goal} := by")
    lines.append("  first")
    lines.extend(f"    | {t}" for t in tactics)
    return "\n".join(lines) + "\n"


@dataclass
class ScreenRun:
    """What one ``qa screen`` run produced: the rows, the exhibits and claims it wrote, the
    record's path, and whether it was a clean pass."""

    subject: str
    rows: list[Row] = field(default_factory=list)
    exhibits: list[str] = field(default_factory=list)
    claims: list[str] = field(default_factory=list)
    record: str | None = None
    problems: list[Diagnostic] = field(default_factory=list)

    @property
    def findings(self) -> list[Row]:
        return [r for r in self.rows if r.is_finding]

    @property
    def clean(self) -> bool:
        """Every row passed: no finding, nothing inconclusive, the statement compiled."""
        return bool(self.rows) and all(r.verdict == "pass" for r in self.rows)

    @property
    def written(self) -> list[str]:
        return [*([self.record] if self.record else []), *self.exhibits, *self.claims]

    def as_dict(self) -> dict[str, Any]:
        return {
            "subject": self.subject,
            "clean": self.clean,
            "checks": [r.as_dict() for r in self.rows],
            "findings": [r.check for r in self.findings],
            "exhibits": list(self.exhibits),
            "claims": list(self.claims),
            "record": self.record,
            "written": self.written,
            "problems": [d.as_dict() for d in self.problems],
        }


Clock = Callable[[], float]
NOTE_CAP = 2000


def _capped(*parts: str | None) -> str | None:
    """The row's note: the non-empty parts joined, within the schema's cap."""
    kept = [p for p in parts if p]
    return "; ".join(kept)[:NOTE_CAP] if kept else None


@dataclass
class _Screening:
    """One run's mutable state: the context, the budgets, the clock and the rows so far."""

    ctx: RunContext
    run: ScreenRun
    date: str
    attempt_budget_s: float
    subject_budget_s: float
    clock: Clock
    tool_version: str
    started: float = 0.0

    def record(self, check: Check, verdict: Verdict, **kw: Any) -> Row:
        row_ = row(
            check,
            verdict,
            tool=SCREEN_TOOL,
            tool_version=self.tool_version,
            timestamp=self.date,
            **kw,
        )
        self.run.rows.append(row_)
        return row_

    def abandon(self, reason: str, *, compile_verdict: Verdict | None = None) -> None:
        """Every screen inconclusive with the reason, after an optional compile row."""
        if compile_verdict is not None:
            self.record("compile", compile_verdict, note=_capped(reason))
        for check in SCREENS:
            self.record(check, "inconclusive", note=_capped(reason))


def screen(  # noqa: PLR0913 — one argument per budget and seam
    ctx: RunContext,
    subject: str,
    *,
    date: str,
    attempt_budget_s: float,
    subject_budget_s: float,
    clock: Clock = time.monotonic,
    contributor: str = SCREEN_CONTRIBUTOR,
    tool_version: str = "0.0.0",
) -> ScreenRun:
    """R3: the screens over ``ctx.claim``'s node — the target's root — through the toolchain seam.

    ``ctx.toolchain`` is wherever the caller put it; the authoritative run puts it in the
    step-3 sandbox (C9), because every attempt elaborates Lean that is trying to prove False.
    The record is written whatever happened, so a run that timed out is a run that says so.
    """
    from opn_gate.steps.toolchain_step import ToolchainStep  # noqa: PLC0415 — an import cycle

    if subject != fidelity.ROOT_SUBJECT:
        msg = (
            f"the screens run on the root statement; {subject!r} is a definition and has nothing "
            "to negate — its pass is compile, brief and backtranslation (F12-Q10)"
        )
        raise QaError("record", msg)
    target_dir = ctx.graph_root / "targets" / ctx.claim.target_id
    s = _Screening(
        ctx, ScreenRun(subject), date, attempt_budget_s, subject_budget_s, clock, tool_version
    )
    s.started = clock()
    resolved = ToolchainStep().run(ctx)
    if not resolved.ok:
        assert resolved.diagnostic is not None
        raise ToolchainMissingError(resolved.diagnostic.message)
    tc: ResolvedToolchain = ctx.data["toolchain"]

    node = _compile_statement(s, tc)
    if node is None:
        s.run.record = _write_run(target_dir, s.run, date)
        return s.run
    plan = _plan(s, target_dir, node)
    if plan is None:
        s.run.record = _write_run(target_dir, s.run, date)
        return s.run
    imports = layout.imports_of(node.statement.text)
    for attempt in plan:
        _run_attempt(s, tc, target_dir, node, attempt, imports=imports, contributor=contributor)
    s.run.record = _write_run(target_dir, s.run, date)
    return s.run


def _compile_statement(s: _Screening, tc: ResolvedToolchain) -> layout.Node | None:
    """Layer 1: stage the definitions and the Context (the statement step) and elaborate the
    statement itself. ``None`` when the run cannot go on; the rows say why."""
    from opn_gate.steps.hazards import StatementStep  # noqa: PLC0415 — an import cycle

    ctx = s.ctx
    compile_started = s.clock()
    try:
        staged = StatementStep().run(ctx)
    except Exception as exc:  # C7: the toolchain blew up; the row says so and the log says why
        log.exception("qa screen: staging %s failed", ctx.claim.node_id)
        s.run.problems.append(Diagnostic("compile", f"{exc.__class__.__name__}: {exc}"))
        s.record(
            "compile",
            "inconclusive",
            elapsed_s=s.clock() - compile_started,
            note=_capped(f"error: {exc.__class__.__name__}: {exc}"),
        )
        s.abandon("the statement could not be staged (layer 1)")
        return None
    node = ctx.node
    if not staged.ok or node is None:
        problem = staged.diagnostic or Diagnostic("compile", "the statement did not stage")
        s.run.problems.append(problem)
        s.record(
            "compile", "fail", elapsed_s=s.clock() - compile_started, note=_capped(problem.message)
        )
        s.abandon("the statement does not compile (layer 1)")
        return None
    src = ctx.workdir / "src"
    module = layout.node_module(node.node_id, "Statement")
    verdict: Verdict = "pass"
    note: str | None = None
    try:
        elab = ctx.toolchain.elaborate(
            tc,
            src / "Nodes" / node.node_id / "Statement.lean",
            module,
            ctx.build_dir,
            root=src,
            timeout_s=s.attempt_budget_s,
        )
        if not elab.ok:
            verdict, note = "fail", _capped("; ".join(m.text for m in elab.errors))
    except subprocess.TimeoutExpired:
        verdict, note = "inconclusive", NOTE_TIMEOUT
    except Exception as exc:  # C7: named on the row, never a crash
        log.exception("qa screen: compiling %s failed", module)
        verdict, note = "inconclusive", _capped(f"error: {exc.__class__.__name__}: {exc}")
    s.record(
        "compile",
        verdict,
        elapsed_s=s.clock() - compile_started,
        budget_s=s.attempt_budget_s,
        note=note,
    )
    if verdict != "pass":
        s.abandon("the statement does not compile (layer 1)")
        return None
    return node


def _plan(s: _Screening, target_dir: Path, node: layout.Node) -> list[Attempt] | None:
    """Layer 2's attempts, or ``None`` with every screen recorded inconclusive when the
    statement's shape or a consequence file cannot be read (Q11)."""
    signature = signature_of(node.statement)
    declared = consequences(target_dir)
    plan: list[Attempt] | Diagnostic
    if isinstance(signature, Diagnostic):
        plan = signature
    elif isinstance(declared, Diagnostic):
        plan = declared
    else:
        plan = attempts_for(signature, declared)
    if isinstance(plan, Diagnostic):
        s.run.problems.append(plan)
        s.abandon(f"{plan.code}: {plan.message}")
        return None
    if not any(a.check == "screen-consequence" for a in plan):
        s.record("screen-consequence", "pass", note=NOTE_NO_CONSEQUENCES)
    return plan


def _run_attempt(  # noqa: PLR0913 — the run, the seam, the attempt and its inputs
    s: _Screening,
    tc: ResolvedToolchain,
    target_dir: Path,
    node: layout.Node,
    attempt: Attempt,
    *,
    imports: list[str],
    contributor: str,
) -> None:
    """One attempt: a row whatever happens, an exhibit and a claim when it proves (R3, R4)."""
    ctx = s.ctx
    attempt_started = s.clock()
    budget = s.attempt_budget_s
    if attempt_started - s.started > s.subject_budget_s:
        s.record(
            attempt.check, "inconclusive", budget_s=budget, note=_capped(attempt.note, NOTE_BUDGET)
        )
        return
    src = ctx.workdir / "src"
    module_imports = [*imports, *(m for m in attempt.extra_imports if m not in imports)]
    source = scratch_source(attempt, imports=module_imports, mathlib=tc.mathlib_sha is not None)
    scratch = src / SCREEN_NAMESPACE / f"{attempt.stem}.lean"
    scratch.parent.mkdir(parents=True, exist_ok=True)
    scratch.write_text(source, encoding="utf-8")
    module = f"{SCREEN_NAMESPACE}.{attempt.stem}"
    decl = f"{SCREEN_NAMESPACE}.{attempt.decl}"
    try:
        outcome = _attempt(ctx, tc, scratch, module, decl, timeout_s=budget)
    except subprocess.TimeoutExpired:
        s.record(
            attempt.check,
            "inconclusive",
            elapsed_s=s.clock() - attempt_started,
            budget_s=budget,
            note=_capped(attempt.note, NOTE_TIMEOUT),
        )
        return
    except Exception as exc:  # C7: the row says so, the log says why
        log.exception("qa screen: %s errored", attempt.check)
        s.record(
            attempt.check,
            "inconclusive",
            elapsed_s=s.clock() - attempt_started,
            budget_s=budget,
            note=_capped(attempt.note, f"error: {exc.__class__.__name__}: {exc}"),
        )
        return
    elapsed = s.clock() - attempt_started
    if outcome is None:  # nothing proved within the budget: the screen found nothing
        s.record(attempt.check, "pass", elapsed_s=elapsed, budget_s=budget, note=attempt.note)
        return
    if isinstance(outcome, Diagnostic):  # it elaborated but the kernel would not have it
        s.record(
            attempt.check,
            "inconclusive",
            elapsed_s=elapsed,
            budget_s=budget,
            note=_capped(attempt.note, f"{outcome.code}: {outcome.message}"),
        )
        return
    # A kernel-checked finding: store it, record it, file it (R3, R4).
    rel, digest = store_exhibit(
        target_dir, exhibit_name(s.run.subject, attempt.check, target_dir), source
    )
    s.run.exhibits.append(rel)
    s.record(
        attempt.check,
        "fail",
        elapsed_s=elapsed,
        budget_s=budget,
        exhibit=rel,
        exhibit_sha256=digest,
        note=_capped(attempt.note, f"proved with axioms {', '.join(sorted(outcome)) or 'none'}"),
    )
    s.run.claims.append(
        file_screen_finding(
            target_dir, node, attempt.check, source, rel, date=s.date, contributor=contributor
        )
    )


def _write_run(target_dir: Path, run: ScreenRun, date: str) -> str:
    path = write(target_dir, run.subject, run.rows, date=date, produced_by=SCREEN_TOOL)
    return relative(target_dir, path)


def _attempt(  # noqa: PLR0913 — the seam's inputs
    ctx: RunContext,
    tc: ResolvedToolchain,
    scratch: Path,
    module: str,
    decl: str,
    *,
    timeout_s: float,
) -> frozenset[str] | Diagnostic | None:
    """Elaborate one scratch theorem. ``None``: it did not prove (a clean screen). A set of
    axioms: it proved and the kernel replayed it under the graph's allowlist (a finding). A
    ``Diagnostic``: it elaborated but replay or the axiom check refused it (inconclusive)."""
    src = ctx.workdir / "src"
    elab = ctx.toolchain.elaborate(
        tc, scratch, module, ctx.build_dir, root=src, timeout_s=timeout_s
    )
    if not elab.ok:
        return None
    replay = ctx.toolchain.kernel_replay(tc, module, [ctx.build_dir], timeout_s=timeout_s)
    if not replay.ok:
        return Diagnostic(
            "kernel-replay-failed",
            "the proof elaborated but leanchecker refused it",
            {"output": replay.output[:2000]},
        )
    axioms = ctx.toolchain.axioms(
        tc, module, decl, [ctx.build_dir], ctx.workdir / "axioms", timeout_s=timeout_s
    )
    if not axioms.ok:
        return Diagnostic("axioms-unreadable", f"could not determine the axioms of {decl}")
    allowed = set(ctx.spec["axiom_allowlist"])
    outside = sorted(a for a in axioms.axioms if a not in allowed)
    if outside:
        return Diagnostic(
            "axiom-not-allowed",
            f"the proof rests on {', '.join(outside)}, outside the graph's allowlist",
            {"axioms": outside},
        )
    return axioms.axioms


# --- the screen's claim, and how a person routes it (R4, Q7) -------------------------------------

CLAIM_SCHEMA = "defect-claim/v2"
SCREEN_FINDING = "screen-finding"
READINGS: tuple[str, ...] = ("misformalization", "refutation")
SCREEN_NOTE = (
    "A kernel-checked proof from the QA screen (F12-R3). It means one of two things and the "
    "screen asserts neither: the statement is a misformalization (route it with a D-16 class; a "
    "D-8 revision follows), or the conjecture is refuted (route it as a refutation; a D-12 "
    "counterexample follows). A curator routes it by appending a claim whose `routes` names "
    "this file (D-9 v3.12)."
)


def defects_dir(node_dir: Path) -> Path:
    return node_dir / "defects"


def theorem_line(statement: layout.Statement) -> int:
    """The 1-based line of the theorem keyword: what D-16's claim points at."""
    m = _THEOREM_HEAD_RE.search(statement.text)
    return statement.text[: m.start()].count("\n") + 1 if m else 1


def file_screen_finding(  # noqa: PLR0913 — one argument per fact the claim carries
    target_dir: Path,
    node: layout.Node,
    check: Check,
    exhibit_text: str,
    qa_exhibit: str,
    *,
    date: str,
    contributor: str = SCREEN_CONTRIBUTOR,
) -> str:
    """R4: file the finding into F08's queue as a ``screen-finding`` claim carrying the exhibit
    and naming both readings. Append-only; the file is named for the run and the screen."""
    doc: dict[str, Any] = {
        "schema": CLAIM_SCHEMA,
        "stmt_ref": node.node_id,
        "class": SCREEN_FINDING,
        "line": theorem_line(node.statement),
        "exhibit": exhibit_text,
        "contributor": contributor,
        "date": date[:10],
        "qa_exhibit": qa_exhibit,
        "readings": list(READINGS),
        "routes": None,
        "note": SCREEN_NOTE,
    }
    schemas.validate(doc, CLAIM_SCHEMA)
    stamp = date.replace("-", "").replace(":", "")
    path = defects_dir(node.path) / f"{stamp}-{contributor}-{check}.yaml"
    if path.exists():
        msg = f"{path} already exists; defect claims are append-only"
        raise QaError("record", msg)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return relative(target_dir, path)


def load_claims(node_dir: Path) -> list[tuple[str, dict[str, Any]]]:
    """Every defect claim under the node, by file name; one that does not parse is skipped with
    a warning, which can only leave a finding *unrouted* — the safe direction."""
    directory = defects_dir(node_dir)
    if not directory.is_dir():
        return []
    out: list[tuple[str, dict[str, Any]]] = []
    for path in sorted(p for p in directory.iterdir() if p.is_file() and p.suffix in SUFFIXES):
        try:
            doc = schemas.load_yaml(path)
        except schemas.SchemaError as exc:
            log.warning("defect claim %s does not validate and routes nothing: %s", path, exc)
            continue
        out.append((path.name, doc))
    return out


def routed_by_claims(target_dir: Path, root_id: str | None = None) -> Routed:
    """R4: a finding is routed when a screen-finding claim names its exhibit and a later claim's
    ``routes`` names that claim — the curator's one act, as an append."""
    node_dir = layout.graph_nodes_dir(graph_root_of(target_dir), target_dir.name) / (
        root_id or root_node(target_dir)
    )
    claims = load_claims(node_dir)
    findings: dict[str, list[str]] = {}
    for name, doc in claims:
        exhibit = doc.get("qa_exhibit")
        if doc.get("class") == SCREEN_FINDING and isinstance(exhibit, str):
            findings.setdefault(exhibit, []).append(name)
    routed_names = {
        str(doc["routes"]["claim"])
        for _, doc in claims
        if isinstance(doc.get("routes"), dict) and "claim" in doc["routes"]
    }

    def routed(finding: Finding) -> bool:
        return any(name in routed_names for name in findings.get(finding.exhibit, []))

    return routed


def route_finding(  # noqa: PLR0913 — one argument per fact of the routing
    target_dir: Path,
    node: layout.Node,
    claim_name: str,
    *,
    reading: str,
    defect_class: str,
    contributor: str,
    date: str,
    note: str | None = None,
) -> str:
    """The curator's routing claim (R4): names the finding and the reading, and carries the
    finding's own exhibit so the gate elaborates the same Lean again."""
    if reading not in READINGS:
        msg = f"reading must be one of {', '.join(READINGS)}, got {reading!r}"
        raise QaError("record", msg)
    found = dict(load_claims(node.path))
    if claim_name not in found or found[claim_name].get("class") != SCREEN_FINDING:
        msg = f"{claim_name} is not a screen-finding claim under {node.node_id}"
        raise QaError("record", msg)
    doc: dict[str, Any] = {
        "schema": CLAIM_SCHEMA,
        "stmt_ref": node.node_id,
        "class": defect_class,
        "line": int(found[claim_name]["line"]),
        "exhibit": str(found[claim_name]["exhibit"]),
        "contributor": contributor,
        "date": date[:10],
        "qa_exhibit": None,
        "routes": {"claim": claim_name, "reading": reading},
        "note": note,
    }
    schemas.validate(doc, CLAIM_SCHEMA)
    stamp = date.replace("-", "").replace(":", "")
    path = defects_dir(node.path) / f"{stamp}-{contributor}.yaml"
    if path.exists():
        msg = f"{path} already exists; defect claims are append-only"
        raise QaError("record", msg)
    path.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return relative(target_dir, path)
