"""The step interface (F00-T5): what every D-4 step receives and returns."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from opn_gate import config
from opn_gate.diagnostic import Diagnostic
from opn_gate.layout import Node
from opn_gate.paths import Change, Claim
from opn_gate.toolchain import Toolchain


@dataclass
class RunContext:
    """Everything a step may read. Steps communicate forward through ``data`` only."""

    graph_root: Path
    claim: Claim
    spec: dict[str, Any]
    gate_spec_hash: str
    changes: list[Change] | None  # None: no diff available (reproduce on a bare tree)
    workdir: Path
    toolchain: Toolchain
    settings: config.Settings
    install_toolchain: bool = False
    node: Node | None = None  # filled by step 2
    data: dict[str, Any] = field(default_factory=dict)

    @property
    def wallclock_s(self) -> float:
        return float(self.spec["step3_caps"]["wallclock_s"])

    @property
    def build_dir(self) -> Path:
        return self.workdir / "build"


@dataclass(frozen=True)
class StepResult:
    ok: bool
    diagnostic: Diagnostic | None = None

    @staticmethod
    def passed() -> StepResult:
        return StepResult(ok=True)

    @staticmethod
    def failed(code: str, message: str, **details: Any) -> StepResult:
        return StepResult(ok=False, diagnostic=Diagnostic(code, message, details))


class Step(Protocol):
    number: int
    name: str

    def run(self, ctx: RunContext) -> StepResult: ...
