"""D-4 step 5: the axiom allowlist; native_decide rejected outright (F00-R6, Q7)."""

from __future__ import annotations

import subprocess

from opn_gate.steps.base import RunContext, StepResult
from opn_gate.steps.replay import PROOF_MODULE
from opn_gate.toolchain import ResolvedToolchain, is_native_decide_axiom


class AxiomsStep:
    number = 5
    name = "axioms"

    def run(self, ctx: RunContext) -> StepResult:
        node = ctx.node
        tc: ResolvedToolchain | None = ctx.data.get("toolchain")
        if node is None or tc is None:
            return StepResult.failed("step-order", "step 5 needs steps 1, 2 and 4 to have passed")
        try:
            result = ctx.toolchain.axioms(
                tc,
                PROOF_MODULE,
                node.statement.decl_name,
                [ctx.build_dir],
                ctx.workdir / "axioms",
                timeout_s=ctx.wallclock_s,
            )
        except subprocess.TimeoutExpired:
            return StepResult.failed(
                "timeout", f"step 5 exceeded the {ctx.wallclock_s:g}s wall-clock cap"
            )
        if not result.ok:
            return StepResult.failed(
                "axioms-unreadable",
                f"could not determine the axioms of {node.statement.decl_name}",
                output=result.output,
            )
        axioms = sorted(result.axioms)
        ctx.data["axioms"] = axioms
        native = [a for a in axioms if is_native_decide_axiom(a)]
        if native:
            return StepResult.failed(
                "native-decide",
                "the proof uses native_decide, which trusts the compiler instead of the kernel",
                axioms=native,
            )
        allowed = set(ctx.spec["axiom_allowlist"])
        outside = [a for a in axioms if a not in allowed]
        if outside:
            return StepResult.failed(
                "axiom-not-allowed",
                f"the proof depends on axioms outside the allowlist: {', '.join(outside)}",
                axioms=outside,
                allowlist=sorted(allowed),
            )
        return StepResult.passed()
