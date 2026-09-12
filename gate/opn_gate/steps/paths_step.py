"""D-4 step 2: permitted paths, layout, statement hash, proof-is-statement (F00-R1, R2, R3, R19)."""

from __future__ import annotations

from pathlib import Path

from opn_gate import layout, paths
from opn_gate.steps import artifact
from opn_gate.steps.artifact import PARTIAL_KEY
from opn_gate.steps.base import RunContext, StepResult


class PathsStep:
    number = 2
    name = "paths"

    def run(self, ctx: RunContext) -> StepResult:  # noqa: PLR0911 — one return per rule
        node_dir = layout.graph_nodes_dir(ctx.graph_root, ctx.claim.target_id) / ctx.claim.node_id
        if ctx.changes is not None:
            proof = node_dir / "Proof.lean"
            proof_text = proof.read_text(encoding="utf-8") if proof.is_file() else ""
            offences = paths.check_paths(
                ctx.changes, ctx.claim, waiver_allowed=paths.mentions_native_decide(proof_text)
            )
            if offences:
                return StepResult.failed(
                    "path-forbidden",
                    f"{len(offences)} change(s) outside the permitted paths",
                    paths=[o.details["path"] for o in offences],
                    offences=[o.message for o in offences],
                )
        loaded = layout.load_node(node_dir, ctx.claim.target_id)
        if isinstance(loaded, list):
            first = loaded[0]
            return StepResult.failed(
                first.code, first.message, **first.details, problems=[d.message for d in loaded]
            )
        ctx.node = loaded
        hash_problem = paths.check_statement_hash(loaded.statement, loaded.meta)
        if hash_problem:  # defence in depth: load_node already refused a hash mismatch above
            return StepResult(ok=False, diagnostic=hash_problem)
        if not loaded.proof_path.is_file():
            # F07-R3, R5 (F11-T4): with no Proof.lean the submission may be a partial — one new
            # assembly under attempts/. Its header and signature are the statement's, like a
            # proof's (D-12 #5: an assembly *is* a proof of S, modulo its holes).
            assembly = partial_assembly(ctx, node_dir)
            if isinstance(assembly, StepResult):
                return assembly
            if assembly is None:
                return StepResult.failed("proof-missing", "the claimed node has no Proof.lean")
            text = assembly.read_text(encoding="utf-8")
            shape_problem = paths.check_proof_is_statement(loaded.statement, text)
            if shape_problem:
                return StepResult(ok=False, diagnostic=shape_problem)
            ctx.data[PARTIAL_KEY] = {
                "path": assembly.relative_to(node_dir).as_posix(),
                "file": str(assembly),
            }
            return StepResult.passed_with(
                "partial-submission",
                f"a partial proof: {assembly.relative_to(node_dir).as_posix()} (D-12 #5)",
                path=assembly.relative_to(node_dir).as_posix(),
            )
        proof_text = loaded.proof_path.read_text(encoding="utf-8")
        # F07-R4 (dispatched in F11-T4): which of D-12's artifacts the file declares decides
        # the shape rule. A proof is the statement with its sorry replaced, textually
        # (F00-R19); a counterexample or a vacuity certificate declares another theorem, whose
        # *type* step 4 checks with the metaprogram. The file says which, never the submitter.
        shape_problem = paths.check_proof_is_statement(loaded.statement, proof_text)
        if shape_problem is None:
            return StepResult.passed()
        kind, _unknown = artifact.declared_kind(loaded.statement.decl_name, proof_text)
        if kind is None or kind == "proof":
            return StepResult(ok=False, diagnostic=shape_problem)  # F00-R19's own words
        return StepResult.passed_with(
            f"{kind}-submission",
            f"Proof.lean declares a {kind} of the statement; its type is step 4's check (D-12)",
            kind=kind,
        )


def partial_assembly(ctx: RunContext, node_dir: Path) -> Path | StepResult | None:
    """The one assembly the diff adds under ``attempts/`` for this node, ``None`` when the diff
    adds none, or the refusal when it adds several. Without a diff (a bare tree) the newest
    assembly on the node is taken, which is what ``reproduce`` sees on a merge commit whose
    diff it has and ``pregate --no-diff`` on a checkout does not."""
    prefix = ctx.claim.node_prefix + "attempts/"
    if ctx.changes is not None:
        added = sorted(
            c.path[len(ctx.claim.node_prefix) :]
            for c in ctx.changes
            if c.status == "A"
            and c.path.startswith(prefix)
            and c.path.endswith(".lean")
            and "/" not in c.path[len(prefix) :]
        )
    else:
        attempts = node_dir / "attempts"
        added = (
            sorted(f"attempts/{p.name}" for p in attempts.glob("*.lean") if p.is_file())
            if attempts.is_dir()
            else []
        )
        added = added[-1:]  # the newest by name: attempts are stamped (F07-R6)
    if not added:
        return None
    if len(added) > 1:
        return StepResult.failed(
            "partial-multiple",
            "a partial submission adds one assembly under attempts/; this one adds "
            + ", ".join(added),
            paths=added,
        )
    return node_dir / added[0]
