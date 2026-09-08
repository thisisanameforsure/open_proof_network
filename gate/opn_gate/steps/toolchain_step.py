"""D-4 step 1: resolve the toolchain from gate-spec.json alone (F00-R4)."""

from __future__ import annotations

from opn_gate.steps.base import RunContext, StepResult
from opn_gate.toolchain import ToolchainMissingError

#: Files a submission might ship to steer the build. They are never read; step 2 rejects them as
#: paths anyway, and this step's only input is the spec.
IGNORED_MANIFESTS: tuple[str, ...] = ("lake-manifest.json", "lean-toolchain", "lakefile.lean")


class ToolchainStep:
    number = 1
    name = "toolchain"

    def run(self, ctx: RunContext) -> StepResult:
        if ctx.spec["mathlib_sha"] is not None:
            return StepResult.failed(
                "mathlib-unsupported",
                "Mathlib-pinned graphs are not supported by this gate version (F10)",
                mathlib_sha=ctx.spec["mathlib_sha"],
            )
        pinned = str(ctx.spec["lean_toolchain"])
        try:
            resolved = ctx.toolchain.resolve(pinned, install=ctx.install_toolchain)
        except ToolchainMissingError as exc:
            return StepResult.failed("toolchain-missing", str(exc), toolchain=pinned)
        ctx.data["toolchain"] = resolved
        return StepResult.passed()
