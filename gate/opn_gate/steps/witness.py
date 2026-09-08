"""D-4 step 7: the non-vacuity witness (F01-R2, R3; Q1).

``Witness.lean`` must exist, elaborate under the pinned toolchain, rest on no axiom outside the
allowlist (in particular not ``sorryAx``), and declare exactly one ``witness`` whose type is
definitionally the expected type the metaprogram derives from ``Statement.lean``.
"""

from __future__ import annotations

import subprocess

from opn_gate import layout
from opn_gate.steps.base import RunContext, StepResult
from opn_gate.toolchain import MetaprogramResult, ResolvedToolchain, WitnessRequest


def metaprogram_failure(step: int, result: MetaprogramResult) -> StepResult:
    """R9: a metaprogram that broke its contract is a step failure carrying its output."""
    return StepResult.failed(
        "metaprogram-failed",
        f"step {step}: metaprogram exited {result.exit_code} without a JSON verdict",
        exit_code=result.exit_code,
        output=result.output,
    )


class WitnessStep:
    number = 7
    name = "witness"

    def run(self, ctx: RunContext) -> StepResult:  # noqa: PLR0911 — one return per R2/R3 rule
        node = ctx.node
        tc: ResolvedToolchain | None = ctx.data.get("toolchain")
        if node is None or tc is None:
            return StepResult.failed("step-order", "step 7 needs steps 1 and 2 to have passed")
        witness_path = node.path / "Witness.lean"
        if not witness_path.is_file():
            return StepResult.failed("witness-missing", "the node has no Witness.lean")
        req = WitnessRequest(
            statement=node.path / "Statement.lean",
            statement_module=layout.node_module(node.node_id, "Statement"),
            decl=node.statement.decl_name,
            witness=witness_path,
            witness_module=layout.node_module(node.node_id, "Witness"),
        )
        try:
            result = ctx.toolchain.witness_type(tc, req, [ctx.build_dir], timeout_s=ctx.wallclock_s)
        except subprocess.TimeoutExpired:
            return StepResult.failed(
                "timeout", f"step 7 exceeded the {ctx.wallclock_s:g}s wall-clock cap"
            )
        if not result.ok and not result.doc:
            return metaprogram_failure(self.number, result)
        if not result.ok:
            error = result.error or "witness check failed"
            code = "witness-shape" if "named `witness`" in error else "witness-elaboration"
            return StepResult.failed(
                code,
                error,
                messages=[m.as_dict() for m in result.messages],
                expected=result.doc.get("expected"),
            )
        expected = str(result.doc.get("expected"))
        witness_type = result.doc.get("witness")
        axioms = sorted(str(a) for a in result.doc.get("witness_axioms") or [])
        ctx.data["witness"] = {"expected": expected, "witness": witness_type, "axioms": axioms}
        if "sorryAx" in axioms:
            return StepResult.failed(
                "witness-sorry", "Witness.lean depends on sorryAx", axioms=axioms
            )
        allowed = set(ctx.spec["axiom_allowlist"])
        outside = [a for a in axioms if a not in allowed]
        if outside:
            return StepResult.failed(
                "witness-axiom",
                f"Witness.lean depends on axioms outside the allowlist: {', '.join(outside)}",
                axioms=outside,
            )
        if result.doc.get("defeq") is not True:
            return StepResult.failed(
                "witness-type-mismatch",
                f"witness has type {witness_type} but the statement's hypotheses need {expected}",
                expected=expected,
                witness=witness_type,
            )
        return StepResult.passed()
