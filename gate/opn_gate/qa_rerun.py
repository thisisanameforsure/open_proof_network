"""The gate re-runs what a QA record claims passed with no file to show for it (F12-T8; D-9 v3.12).

A clean screen and a compile leave no exhibit (F12-Q15), so a ``qa/v1`` record whose every floor
row says ``verdict: pass, exhibit: null`` reads the same whether ``opn-gate qa screen`` wrote it
or a curator typed it (finding D3). R15 closes the forgery for rows that name a file — the hash
on the row, the replay before a grade counts it. For rows that name none, the project owner
decided on 2026-09-13 that the pull request adding the record is where they are checked: the gate
re-runs, inside the step-3 sandbox and on the statement as it stands at head, every compile and
soundness screen the record says passed without an exhibit, and refuses the pull request naming
each row the re-run does not also pass.

What is re-run and what is not, and why:

- **compile and the four screens** with ``verdict: pass`` and no exhibit — re-run. The root's
  are ``qa.screen`` itself; a definition's compile is the target's definitions built through the
  same seam (a definition has no screens, F12-Q10). A re-run that finds something, times out,
  runs out of budget or errors disagrees with a recorded pass (C7: never a clean pass).
- **brief and backtranslation** — not re-run: each asks a model, and the gate job holds no model
  key and must not (C8). They stay held to R15 and the writer's coherence rules (F12-Q18), and a
  brief never raises a grade on its own (R2).
- **any row naming an exhibit file** — not re-run: R15's hash and replay cover it.
- **a row that records no pass** — nothing to contradict.

The re-run writes what ``qa screen`` writes (a record, and on a finding an exhibit and a claim)
into a scratch copy of the tree, never into the checkout the gate job is checking.
"""

from __future__ import annotations

import logging
import shutil
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from opn_gate import config, defs, fidelity, layout, qa, schemas
from opn_gate.diagnostic import Diagnostic
from opn_gate.paths import Claim, Located
from opn_gate.steps.base import RunContext
from opn_gate.toolchain import ResolvedToolchain, Toolchain, ToolchainMissingError

log = logging.getLogger(__name__)

TOOL = "opn-gate qa-rerun"
#: The checks whose clean pass leaves no file, and so the only ones a re-run can confirm.
RERUN_CHECKS: tuple[qa.Check, ...] = ("compile", *qa.SCREENS)
#: The checks that ask a model: the gate job holds no key for one (C8).
MODEL_CHECKS: tuple[qa.Check, ...] = ("brief", "backtranslation")

CODE_DISAGREES = "qa-rerun-disagrees"
CODE_UNVERIFIABLE = "qa-rerun-unverifiable"

REASON_MODEL = (
    "asks a model, and the gate job holds no model key (C8); held to R15 and the writer's "
    "coherence rules instead (F12-Q18), and a brief never raises a grade on its own (R2)"
)
REASON_EXHIBIT = (
    "names an exhibit file: trusted by its SHA-256 and replayed before a grade counts it (R15)"
)
REASON_NOTHING_CLAIMED = "records no pass, so it claims nothing a re-run could contradict"
REASON_DEFINITION_SCREEN = (
    "a definition has no screens (F12-Q10); the row is outside its floor and counts for nothing"
)
REASON_EQUIVALENCE = (
    "equivalence is outside the floor (F12-Q3) and is evidence only through its exhibit (R2, R15)"
)


@dataclass(frozen=True)
class Checked:
    """One recorded pass and what the re-run at head said about the same check."""

    record: str  # relative to the graph root
    subject: str
    check: str
    rerun: tuple[str, ...]  # the re-run's verdicts for the check (a consequence screen may be many)
    notes: tuple[str, ...] = ()

    @property
    def agrees(self) -> bool:
        return agrees(self.rerun)

    def as_dict(self) -> dict[str, Any]:
        return {
            "record": self.record,
            "subject": self.subject,
            "check": self.check,
            "recorded": "pass",
            "rerun": list(self.rerun),
            "agrees": self.agrees,
            "notes": list(self.notes),
        }


@dataclass(frozen=True)
class NotRerun:
    """A row the gate does not re-run, with the reason it gives."""

    record: str
    subject: str
    check: str
    verdict: str
    reason: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "record": self.record,
            "subject": self.subject,
            "check": self.check,
            "verdict": self.verdict,
            "reason": self.reason,
        }


@dataclass
class Report:
    records: list[str]
    checked: list[Checked] = field(default_factory=list)
    not_rerun: list[NotRerun] = field(default_factory=list)
    problems: list[Diagnostic] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.problems

    def as_dict(self, max_bytes: int | None = None) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "records": list(self.records),
            "checked": [c.as_dict() for c in self.checked],
            "not_rerun": [n.as_dict() for n in self.not_rerun],
            "problems": [d.as_dict(max_bytes) for d in self.problems],
        }


#: The seam: the fresh rows for ``(target_id, subject)`` as the tree stands at head.
Rerun = Callable[[str, str], Sequence[qa.Row]]


def records_in(located: Iterable[Located]) -> list[str]:
    """The QA records a pull request adds — what the classifier reports as needing the re-run."""
    return sorted(loc.path for loc in located if loc.role == "qa-record")


def agrees(rerun: Sequence[str]) -> bool:
    """A recorded pass stands only when the re-run ran the check and every run of it passed."""
    return bool(rerun) and all(v == "pass" for v in rerun)


def reason_not_rerun(subject: str, row: qa.Row) -> str | None:
    """Why the gate leaves a row alone, or ``None`` when the row is a pass it must re-run."""
    if row.check in MODEL_CHECKS:
        return REASON_MODEL
    if row.exhibit is not None:
        return REASON_EXHIBIT
    if row.verdict != "pass":
        return REASON_NOTHING_CLAIMED
    if row.check not in RERUN_CHECKS:
        return REASON_EQUIVALENCE
    if subject != fidelity.ROOT_SUBJECT and row.check in qa.SCREENS:
        return REASON_DEFINITION_SCREEN
    return None


def _record_at(graph_root: Path, rel: str) -> tuple[Path, qa.Record] | Diagnostic:
    path = (graph_root / rel).resolve()
    parts = Path(rel).parts
    if len(parts) < 4 or parts[0] != "targets" or parts[2] != qa.QA_DIR:
        return Diagnostic(
            CODE_UNVERIFIABLE, f"{rel} is not a QA record path (targets/<id>/qa/)", {"record": rel}
        )
    target_dir = graph_root / "targets" / parts[1]
    for records in qa.load(target_dir).values():
        for record in records:
            if record.path is not None and record.path.resolve() == path:
                return target_dir, record
    return Diagnostic(CODE_UNVERIFIABLE, f"{rel} is not in the tree at head", {"record": rel})


def verify(graph_root: Path, record_paths: Sequence[str], rerun: Rerun) -> Report:
    """Re-run every claimed pass the records carry and name each disagreement.

    ``rerun`` is called at most once per ``(target, subject)``, and only when some record for it
    carries a pass the gate re-runs — a record of briefs alone starts no toolchain.
    """
    report = Report(records=list(record_paths))
    fresh: dict[tuple[str, str], Sequence[qa.Row]] = {}
    for rel in record_paths:
        found = _record_at(graph_root, rel)
        if isinstance(found, Diagnostic):
            report.problems.append(found)
            continue
        target_dir, record = found
        claimed: list[qa.Row] = []
        for row in record.checks:
            reason = reason_not_rerun(record.subject, row)
            if reason is None:
                claimed.append(row)
            else:
                report.not_rerun.append(
                    NotRerun(rel, record.subject, row.check, row.verdict, reason)
                )
        if not claimed:
            continue
        problem = _unverifiable(target_dir, record, rel)
        if problem is not None:
            report.problems.append(problem)
            continue
        key = (target_dir.name, record.subject)
        if key not in fresh:
            fresh[key] = rerun(*key)
        for row in claimed:
            same = [r for r in fresh[key] if r.check == row.check]
            checked = Checked(
                rel,
                record.subject,
                row.check,
                tuple(r.verdict for r in same),
                tuple(r.note for r in same if r.note),
            )
            report.checked.append(checked)
            if not checked.agrees:
                report.problems.append(_disagreement(checked))
    return report


def _unverifiable(target_dir: Path, record: qa.Record, rel: str) -> Diagnostic | None:
    """A record for another statement or another pin cannot be checked against head (R5)."""
    try:
        current = qa.subject_hash(target_dir, record.subject)
    except qa.QaError as exc:
        return Diagnostic(CODE_UNVERIFIABLE, f"{rel}: {exc}", {"record": rel})
    if record.stale(current, qa.spec_of(target_dir)):
        return Diagnostic(
            CODE_UNVERIFIABLE,
            f"{rel} is pinned to a statement hash, toolchain or Mathlib other than the tree's at "
            "head, so its passes cannot be re-run here; run `opn-gate qa screen` at head (R5)",
            {
                "record": rel,
                "statement_hash": record.statement_hash,
                "current_statement_hash": current,
            },
        )
    return None


def _disagreement(checked: Checked) -> Diagnostic:
    said = ", ".join(checked.rerun) if checked.rerun else "nothing (the check did not run)"
    why = f" ({'; '.join(checked.notes)})" if checked.notes else ""
    return Diagnostic(
        CODE_DISAGREES,
        f"{checked.record}: {checked.subject} {checked.check} is recorded pass, but the gate's "
        f"re-run at head says {said}{why}; a pass with no exhibit stands only when the gate "
        "reproduces it (F12-T8, C7)",
        checked.as_dict(),
    )


# --- the re-run itself: ``qa screen`` over a scratch copy of the head tree ----------------------


def head_copy(graph_root: Path, dest: Path) -> Path:
    """The tree at head, copied without its history, for the re-run to write into — the screen
    records its run and files its findings, and none of that belongs in the checkout."""
    if not dest.is_dir():
        shutil.copytree(graph_root, dest, ignore=shutil.ignore_patterns(".git"))
    return dest


def context(  # noqa: PLR0913 — one argument per fact the run needs
    copy_root: Path,
    target_id: str,
    toolchain: Toolchain,
    workdir: Path,
    settings: config.Settings,
    *,
    install: bool = False,
) -> RunContext:
    """A run over the copy's root node, as ``qa screen`` builds one."""
    target_dir = copy_root / "targets" / target_id
    spec_path = layout.gate_spec_path(copy_root, target_id)
    return RunContext(
        graph_root=copy_root,
        claim=Claim(target_id, qa.root_node(target_dir)),
        spec=schemas.load_json(spec_path, "gate-spec/v1"),
        gate_spec_hash=schemas.content_hash(spec_path.read_bytes()),
        changes=None,
        workdir=workdir,
        toolchain=toolchain,
        settings=settings,
        install_toolchain=install,
    )


def rerun_subject(
    ctx: RunContext,
    subject: str,
    *,
    date: str,
    attempt_budget_s: float,
    subject_budget_s: float,
) -> list[qa.Row]:
    """The fresh rows for one subject. ``ctx.graph_root`` must be a copy (``head_copy``)."""
    if subject == fidelity.ROOT_SUBJECT:
        run = qa.screen(
            ctx,
            subject,
            date=date,
            attempt_budget_s=attempt_budget_s,
            subject_budget_s=subject_budget_s,
        )
        return list(run.rows)
    return [_compile_definition(ctx, subject, date=date, timeout_s=attempt_budget_s)]


def _compile_definition(ctx: RunContext, subject: str, *, date: str, timeout_s: float) -> qa.Row:
    """A definition's layer 1: the target's definitions built through the seam, in order."""
    from opn_gate.steps.toolchain_step import ToolchainStep  # noqa: PLC0415 — an import cycle

    resolved = ToolchainStep().run(ctx)
    if not resolved.ok:
        assert resolved.diagnostic is not None
        raise ToolchainMissingError(resolved.diagnostic.message)
    tc: ResolvedToolchain = ctx.data["toolchain"]
    target_dir = ctx.graph_root / "targets" / ctx.claim.target_id
    try:
        problem = defs.compile_all(ctx.toolchain, tc, target_dir, ctx.workdir, timeout_s=timeout_s)
    except Exception as exc:  # C7: named on the row, logged, never a crash and never a pass
        log.exception("qa-rerun: compiling the definitions of %s failed", ctx.claim.target_id)
        return _row(subject, "inconclusive", date, f"error: {exc.__class__.__name__}: {exc}")
    if problem is None:
        return _row(subject, "pass", date, None)
    verdict: qa.Verdict = "inconclusive" if problem.code == "timeout" else "fail"
    return _row(subject, verdict, date, f"{problem.code}: {problem.message}")


def _row(subject: str, verdict: qa.Verdict, date: str, note: str | None) -> qa.Row:
    return qa.row(
        "compile",
        verdict,
        tool=TOOL,
        tool_version="0.0.0",
        timestamp=date,
        note=f"definition {subject}" + (f"; {note}" if note else ""),
    )
