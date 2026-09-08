"""The gate pipeline: steps in D-4 order, stop at the first failure, always a verdict (F00-R7, R18).

``run_steps`` never raises for a step's sake: an unexpected exception inside a step is that
step's failure, recorded with the exception class and message (C7). ``run_submission`` is the
entrypoint the three invocations share (D-4: pregate.sh, the authoritative gate, reproduce.sh);
only the authoritative one passes a precheck policy, which may bounce before any step runs.
"""

from __future__ import annotations

import logging
import traceback
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Literal

from opn_gate import bounce
from opn_gate.diagnostic import Diagnostic
from opn_gate.steps import RunContext, Step, StepResult, default_steps

log = logging.getLogger(__name__)

VerdictKind = Literal["pass", "fail", "bounced"]


@dataclass(frozen=True)
class StepRecord:
    step: int
    name: str
    result: Literal["pass", "fail", "skipped"]
    diagnostic: Diagnostic | None = None


@dataclass(frozen=True)
class Verdict:
    verdict: VerdictKind
    steps: tuple[StepRecord, ...]
    first_failing_step: int | None = None
    diagnostic: Diagnostic | None = None
    data: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.verdict == "pass"

    def as_dict(self, max_bytes: int | None = None) -> dict[str, Any]:
        return {
            "verdict": self.verdict,
            "first_failing_step": self.first_failing_step,
            "diagnostic": None if self.diagnostic is None else self.diagnostic.as_dict(max_bytes),
            "steps": [
                {
                    "step": s.step,
                    "name": s.name,
                    "result": s.result,
                    "diagnostic": None if s.diagnostic is None else s.diagnostic.as_dict(max_bytes),
                }
                for s in self.steps
            ],
        }


def _guarded(step: Step, ctx: RunContext) -> StepResult:
    try:
        return step.run(ctx)
    except Exception as exc:  # R18: any exception is this step's failure, never a crash
        log.exception("step %d (%s) raised", step.number, step.name)
        return StepResult.failed(
            "unexpected-error",
            f"{type(exc).__name__}: {exc}",
            exception=type(exc).__name__,
            traceback=traceback.format_exc(limit=5),
        )


def run_steps(ctx: RunContext, steps: Sequence[Step] | None = None) -> Verdict:
    """Run ``steps`` (default: this version's D-4 steps) and stop at the first failure."""
    ordered = sorted(steps if steps is not None else default_steps(), key=lambda s: s.number)
    records: list[StepRecord] = []
    failed_at: int | None = None
    diagnostic: Diagnostic | None = None
    for step in ordered:
        if failed_at is not None:
            records.append(StepRecord(step.number, step.name, "skipped"))
            continue
        result = _guarded(step, ctx)
        if result.ok:
            records.append(StepRecord(step.number, step.name, "pass"))
        else:
            failed_at = step.number
            diagnostic = result.diagnostic or Diagnostic("failed", "step failed without detail")
            records.append(StepRecord(step.number, step.name, "fail", diagnostic))
            log.info("step %d (%s) failed: %s", step.number, step.name, diagnostic.code)
    return Verdict(
        verdict="pass" if failed_at is None else "fail",
        steps=tuple(records),
        first_failing_step=failed_at,
        diagnostic=diagnostic,
        data=dict(ctx.data),
    )


def run_submission(
    ctx: RunContext,
    *,
    precheck: bounce.PrecheckPolicy | None = None,
    steps: Sequence[Step] | None = None,
) -> Verdict:
    """The shared entrypoint. With a policy, the bounce rule runs first (F00-R13)."""
    if precheck is not None:
        decision = bounce.evaluate(precheck)
        ctx.data["precheck_attestation"] = {
            "hash": decision.attestation_hash,
            "signature_kind": decision.signature_kind,
        }
        if decision.bounced:
            return Verdict(
                verdict="bounced",
                steps=(),
                diagnostic=Diagnostic("bounced", decision.reason or "bounced", decision.details),
                data=dict(ctx.data),
            )
    return run_steps(ctx, steps)
