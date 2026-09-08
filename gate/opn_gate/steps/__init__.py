"""The D-4 steps this gate version implements, in order (F00: 1, 2, 4, 5; F01: 7, 8)."""

from __future__ import annotations

from opn_gate.steps.axioms import AxiomsStep
from opn_gate.steps.base import RunContext, Step, StepResult
from opn_gate.steps.deps import DepsStep
from opn_gate.steps.paths_step import PathsStep
from opn_gate.steps.replay import KernelReplayStep
from opn_gate.steps.toolchain_step import ToolchainStep
from opn_gate.steps.witness import WitnessStep


def default_steps() -> list[Step]:
    """The D-4 steps this gate version implements: 1, 2, 4, 5 (F00) and 7, 8 (F01)."""
    return [
        ToolchainStep(),
        PathsStep(),
        KernelReplayStep(),
        AxiomsStep(),
        WitnessStep(),
        DepsStep(),
    ]


__all__ = ["RunContext", "Step", "StepResult", "default_steps"]
