"""D-4 step 5: the axiom allowlist; ``native_decide`` only under a recorded waiver (F00-R6, Q7;
F02-R8).

A proof that used ``native_decide`` rests on the compiler, not the kernel. It passes this step
only when the submission carries ``waivers/native_decide.yaml`` (``waiver/v1``: justification and
author); the pass is recorded on the step and the attestation's ``trust_base`` becomes
``compiler`` (F02-R9). A waiver file without a ``native_decide`` use is itself a failure: the
path is permitted only when needed (R8).
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from opn_gate import layout, schemas
from opn_gate.steps.base import RunContext, StepResult
from opn_gate.steps.replay import PROOF_MODULE
from opn_gate.toolchain import ResolvedToolchain, is_native_decide_axiom

WAIVER_SCHEMA = "waiver/v1"
WAIVER_FILE = Path("waivers") / "native_decide.yaml"


def load_waiver(node_dir: Path) -> dict[str, Any] | schemas.SchemaError | None:
    """The node's waiver document, ``None`` when absent, or the error when it does not validate."""
    path = node_dir / WAIVER_FILE
    if not path.is_file():
        return None
    try:
        return schemas.load_yaml(path, WAIVER_SCHEMA)
    except schemas.SchemaError as exc:
        return exc


class AxiomsStep:
    number = 5
    name = "axioms"

    def run(self, ctx: RunContext) -> StepResult:  # noqa: PLR0911 — one return per rule
        node = ctx.node
        tc: ResolvedToolchain | None = ctx.data.get("toolchain")
        if node is None or tc is None:
            return StepResult.failed("step-order", "step 5 needs steps 1, 2 and 4 to have passed")
        try:
            result = ctx.toolchain.axioms(
                tc,
                layout.node_module(node.node_id, PROOF_MODULE),
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
        waiver = load_waiver(node.path)
        if isinstance(waiver, schemas.SchemaError):
            return StepResult.failed(
                "waiver-invalid",
                f"{WAIVER_FILE} does not validate against {WAIVER_SCHEMA}: {waiver}",
                path=str(WAIVER_FILE),
            )
        if native and waiver is None:
            return StepResult.failed(
                "native-decide-unwaived",
                "the proof uses native_decide, which trusts the compiler instead of the kernel; "
                f"it passes only with a recorded waiver at {WAIVER_FILE} (waiver/v1)",
                axioms=native,
            )
        if waiver is not None and not native:
            return StepResult.failed(
                "waiver-unneeded",
                f"{WAIVER_FILE} is present but the proof does not use native_decide; the path is "
                "permitted only when it is needed",
                path=str(WAIVER_FILE),
            )
        allowed = set(ctx.spec["axiom_allowlist"])
        outside = [a for a in axioms if a not in allowed and not is_native_decide_axiom(a)]
        if outside:
            return StepResult.failed(
                "axiom-not-allowed",
                f"the proof depends on axioms outside the allowlist: {', '.join(outside)}",
                axioms=outside,
                allowlist=sorted(allowed),
            )
        if waiver is not None:
            record = {
                "kind": "native_decide",
                "author": str(waiver["author"]),
                "justification": str(waiver["justification"]),
                "axioms": native,
            }
            ctx.data["waiver"] = record
            return StepResult.passed_with(
                "native-decide-waived",
                "waiver: native_decide — the proof trusts the compiler under a recorded waiver; "
                "the approving review must name it and the node is flagged permanently",
                waiver=record,
            )
        return StepResult.passed()
