"""D-4 step 2: permitted paths, layout, statement hash, proof-is-statement (F00-R1, R2, R3, R19)."""

from __future__ import annotations

from opn_gate import layout, paths
from opn_gate.steps.base import RunContext, StepResult


class PathsStep:
    number = 2
    name = "paths"

    def run(self, ctx: RunContext) -> StepResult:
        if ctx.changes is not None:
            offences = paths.check_paths(ctx.changes, ctx.claim)
            if offences:
                return StepResult.failed(
                    "path-forbidden",
                    f"{len(offences)} change(s) outside the permitted paths",
                    paths=[o.details["path"] for o in offences],
                    offences=[o.message for o in offences],
                )
        node_dir = layout.graph_nodes_dir(ctx.graph_root, ctx.claim.target_id) / ctx.claim.node_id
        loaded = layout.load_node(node_dir, ctx.claim.target_id)
        if isinstance(loaded, list):
            first = loaded[0]
            return StepResult.failed(
                first.code, first.message, **first.details, problems=[d.message for d in loaded]
            )
        ctx.node = loaded
        hash_problem = paths.check_statement_hash(loaded.statement, loaded.meta)
        if hash_problem:
            return StepResult(ok=False, diagnostic=hash_problem)
        if not loaded.proof_path.is_file():
            return StepResult.failed("proof-missing", "the claimed node has no Proof.lean")
        proof_text = loaded.proof_path.read_text(encoding="utf-8")
        shape_problem = paths.check_proof_is_statement(loaded.statement, proof_text)
        if shape_problem:
            return StepResult(ok=False, diagnostic=shape_problem)
        return StepResult.passed()
