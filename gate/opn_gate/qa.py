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
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml

from opn_gate import fidelity, layout, schemas
from opn_gate import graph as graphmod
from opn_gate.diagnostic import Diagnostic

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
