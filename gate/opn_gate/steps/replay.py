"""D-4 step 4: elaborate, then replay every declaration through the kernel from clean (F00-R5)."""

from __future__ import annotations

import subprocess

from opn_gate.steps.base import RunContext, StepResult
from opn_gate.toolchain import ResolvedToolchain

PROOF_MODULE = "Proof"
CONTEXT_MODULE = "Context"


class KernelReplayStep:
    number = 4
    name = "kernel-replay"

    def run(self, ctx: RunContext) -> StepResult:
        node = ctx.node
        tc: ResolvedToolchain | None = ctx.data.get("toolchain")
        if node is None or tc is None:
            return StepResult.failed("step-order", "step 4 needs steps 1 and 2 to have passed")
        build = ctx.build_dir
        try:
            for module in (CONTEXT_MODULE, PROOF_MODULE):
                source = node.path / f"{module}.lean"
                elab = ctx.toolchain.elaborate(tc, source, module, build, timeout_s=ctx.wallclock_s)
                if not elab.ok:
                    return StepResult.failed(
                        "elaboration-failed",
                        f"{module}.lean does not elaborate",
                        module=module,
                        messages=[m.as_dict() for m in elab.errors or elab.messages],
                        stderr=elab.stderr,
                    )
            replay = ctx.toolchain.kernel_replay(
                tc, PROOF_MODULE, [build], timeout_s=ctx.wallclock_s
            )
        except subprocess.TimeoutExpired as exc:
            return StepResult.failed(
                "timeout",
                f"step 4 exceeded the {ctx.wallclock_s:g}s wall-clock cap",
                cmd=str(exc.cmd),
            )
        if not replay.ok:
            return StepResult.failed(
                "kernel-replay-failed",
                "leanchecker --fresh rejected the module",
                output=replay.output,
            )
        return StepResult.passed()
