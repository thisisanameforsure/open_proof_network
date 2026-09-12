"""D-4 step 1: resolve the toolchain from gate-spec.json alone (F00-R4) — and, for a graph that
pins Mathlib, the Mathlib checkout built by that toolchain (F11-R6; D-7)."""

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
        pinned = str(ctx.spec["lean_toolchain"])
        raw_sha = ctx.spec["mathlib_sha"]
        mathlib_sha = str(raw_sha) if raw_sha is not None else None
        try:
            resolved = ctx.toolchain.resolve(
                pinned, install=ctx.install_toolchain, mathlib_sha=mathlib_sha
            )
        except ToolchainMissingError as exc:
            return StepResult.failed(
                "toolchain-missing", str(exc), toolchain=pinned, mathlib_sha=mathlib_sha
            )
        ctx.data["toolchain"] = resolved
        if mathlib_sha is None:
            return StepResult.passed()
        # F11-AC11: the pin is reported, never where this host keeps it — the attestation is a
        # function of the tree and the pins, not of the runner's disk (D-5). Whether the oleans
        # were in the image or fetched by the install script is likewise not a fact about the tree.
        return StepResult.passed_with(
            "mathlib-pinned",
            f"Mathlib {mathlib_sha[:12]} resolved from the pinned checkout",
            mathlib_sha=mathlib_sha,
            packages=len(resolved.library_path),
        )
