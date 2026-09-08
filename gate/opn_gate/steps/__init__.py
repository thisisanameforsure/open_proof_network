"""The D-4 steps this gate version implements, in order (F00: 1, 2, 4, 5)."""

from __future__ import annotations

from opn_gate.steps.axioms import AxiomsStep
from opn_gate.steps.base import RunContext, Step, StepResult
from opn_gate.steps.paths_step import PathsStep
from opn_gate.steps.replay import KernelReplayStep
from opn_gate.steps.toolchain_step import ToolchainStep


def default_steps() -> list[Step]:
    return [ToolchainStep(), PathsStep(), KernelReplayStep(), AxiomsStep()]


__all__ = ["RunContext", "Step", "StepResult", "default_steps"]
