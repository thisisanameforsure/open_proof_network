"""D-4 step 2: permitted paths, layout, statement hash, proof-is-statement (F00-R1, R2, R3, R19)."""

from __future__ import annotations

from pathlib import Path

from opn_gate import carried, layout, paths
from opn_gate.diagnostic import Diagnostic
from opn_gate.steps import artifact
from opn_gate.steps.artifact import ALTERNATE_KEY, PARTIAL_KEY
from opn_gate.steps.base import RunContext, StepResult


class PathsStep:
    number = 2
    name = "paths"

    def run(self, ctx: RunContext) -> StepResult:  # noqa: PLR0911, PLR0912 — one per rule
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
        alternate = alternate_file(ctx, node_dir)
        if isinstance(alternate, StepResult):
            return alternate
        if alternate is not None:
            return stray_witnesses(ctx) or take_alternate(ctx, loaded, node_dir, alternate)
        if not loaded.proof_path.is_file():
            # F07-R3, R5 (F11-T4): with no Proof.lean the submission may be a partial — one new
            # assembly under attempts/. Its header and signature are the statement's, like a
            # proof's (D-12 #5: an assembly *is* a proof of S, modulo its holes).
            assembly = partial_assembly(ctx, node_dir)
            if isinstance(assembly, StepResult):
                return assembly
            if assembly is None:
                return stray_witnesses(ctx) or StepResult.failed(
                    "proof-missing", "the claimed node has no Proof.lean"
                )
            text = assembly.read_text(encoding="utf-8")
            refusal = partial_refusal(loaded.statement, node_dir, text)
            if refusal is not None:
                return StepResult(ok=False, diagnostic=refusal)
            ctx.data[PARTIAL_KEY] = {
                "path": assembly.relative_to(node_dir).as_posix(),
                "file": str(assembly),
            }
            # F07-R23 (D-29 v3.24): the witnesses the partial carries for its holes, read and
            # held to the grammar here, before any Lean is built; step 7 checks each one.
            witnesses, problem = carried_witnesses(ctx, node_dir, assembly)
            if problem is not None:
                return StepResult(ok=False, diagnostic=problem)
            if witnesses:  # absent when nothing is carried: the record is what it was
                ctx.data[PARTIAL_KEY][carried.PARTIAL_WITNESSES_KEY] = [
                    {"hole": w.hole, "path": w.path, "file": str(node_dir / w.path)}
                    for w in witnesses
                ]
            return StepResult.passed_with(
                "partial-submission",
                f"a partial proof: {assembly.relative_to(node_dir).as_posix()} (D-12 #5)",
                path=assembly.relative_to(node_dir).as_posix(),
            )
        stray = stray_witnesses(ctx)
        if stray is not None:
            return stray
        proof_text = loaded.proof_path.read_text(encoding="utf-8")
        # F07-R4 (dispatched in F11-T4): which of D-12's artifacts the file declares decides
        # the shape rule. A proof is the statement with its sorry replaced, textually
        # (F00-R19); a counterexample or a vacuity certificate declares another theorem, whose
        # *type* step 4 checks with the metaprogram. The file says which, never the submitter.
        shape_problem = paths.check_proof_is_statement(
            loaded.statement, proof_text, node_id=ctx.claim.node_id
        )
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


def added_witnesses(ctx: RunContext) -> list[str]:
    """The carried-witness files the diff adds under this node's ``attempts/``, as paths under
    the node; nothing on a bare tree, which has no diff to say what is new."""
    if ctx.changes is None:
        return []
    prefix = ctx.claim.node_prefix + carried.ATTEMPTS
    return sorted(
        c.path[len(ctx.claim.node_prefix) :]
        for c in ctx.changes
        if c.status == "A"
        and c.path.startswith(prefix)
        and "/" not in c.path[len(prefix) :]
        and carried.is_carried(c.path[len(prefix) :])
    )


def stray_witnesses(ctx: RunContext) -> StepResult | None:
    """R23: a carried witness in a submission that is not a partial is refused by name. The
    classifier refuses the same diff as fitting no mode; a precheck never classifies, so step 2
    says it too."""
    added = added_witnesses(ctx)
    return StepResult(ok=False, diagnostic=carried.without_partial(added)) if added else None


def carried_witnesses(
    ctx: RunContext, node_dir: Path, assembly: Path
) -> tuple[list[carried.Carried], Diagnostic | None]:
    """R23: the witnesses this partial carries, or why one of its files is not one. With a diff,
    every witness file it adds must be attached to the one assembly it adds; on a bare tree the
    files attached to the assembly taken (the newest) are the submission's."""
    assembly_rel = assembly.relative_to(node_dir).as_posix()
    if ctx.changes is not None:
        names = added_witnesses(ctx)
    else:
        attempts = node_dir / "attempts"
        on_disk = {
            f"{carried.ATTEMPTS}{p.name}": ""
            for p in attempts.iterdir()
            if p.is_file() and carried.is_carried(p.name)
        }
        names = sorted(carried.attached_to(assembly_rel, on_disk))
    files = {rel: (node_dir / rel).read_text(encoding="utf-8") for rel in names}
    return carried.read(assembly_rel, files)


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
            and not c.path.endswith(paths.ALTERNATE_SUFFIX)
            and "/" not in c.path[len(prefix) :]
        )
    else:
        attempts = node_dir / "attempts"
        added = (
            sorted(
                f"attempts/{p.name}"
                for p in attempts.glob("*.lean")
                if p.is_file() and not p.name.endswith(paths.ALTERNATE_SUFFIX)
            )
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


def alternate_file(ctx: RunContext, node_dir: Path) -> Path | StepResult | None:
    """D-25 v3.13: the one ``attempts/*-alternate.lean`` the diff adds to this node, ``None`` when
    it adds none, or the refusal when it adds several. Only a diff can say which file is new, so
    a bare tree has no alternate and step 2 checks the node's ``Proof.lean`` as it always did."""
    if ctx.changes is None:
        return None
    prefix = ctx.claim.node_prefix + "attempts/"
    added = sorted(
        c.path[len(ctx.claim.node_prefix) :]
        for c in ctx.changes
        if c.status == "A"
        and c.path.startswith(prefix)
        and c.path.endswith(paths.ALTERNATE_SUFFIX)
        and "/" not in c.path[len(prefix) :]
    )
    if not added:
        return None
    if len(added) > 1:
        return StepResult.failed(
            "alternate-multiple",
            "a pull request adds one alternate proof (D-25); this one adds " + ", ".join(added),
            paths=added,
        )
    return node_dir / added[0]


def take_alternate(
    ctx: RunContext, loaded: layout.Node, node_dir: Path, alternate: Path
) -> StepResult:
    """R7: an alternate is held to a proof's shape — the statement with its sorry replaced
    (F00-R19) — and recorded for step 4, which stages it as the node's Proof module. A file
    declaring a counterexample or vacuity certificate of a proved statement is not an alternate."""
    rel = alternate.relative_to(node_dir).as_posix()
    if not loaded.proof_path.is_file():  # precheck never classifies, so step 2 says it too
        return StepResult.failed(
            "alternate-unproved",
            f"{ctx.claim.node_id} has no merged Proof.lean, so {rel} has nothing to be an "
            "alternate to: submit it as the node's Proof.lean (D-25)",
            path=rel,
        )
    text = alternate.read_text(encoding="utf-8")
    shape_problem = paths.check_proof_is_statement(
        loaded.statement, text, node_id=ctx.claim.node_id
    )
    if shape_problem is not None:
        kind, _unknown = artifact.declared_kind(loaded.statement.decl_name, text)
        if kind is not None and kind != "proof":
            return StepResult.failed(
                "alternate-not-proof",
                f"{rel} declares a {kind} of a statement already proved; an alternate is another "
                "proof of it (D-25), and a merged proof beside a refutation is a defect claim "
                "(D-15), not a submission",
                path=rel,
                kind=kind,
            )
        return StepResult(ok=False, diagnostic=shape_problem)
    ctx.data[ALTERNATE_KEY] = {"path": rel, "file": str(alternate)}
    return StepResult.passed_with(
        "alternate-submission",
        f"an alternate proof: {rel} (D-25); the node's Proof.lean is unchanged",
        path=rel,
    )


def partial_refusal(statement: layout.Statement, node_dir: Path, text: str) -> Diagnostic | None:
    """Why step 2 refuses an assembly, or ``None``. Its header and signature are the statement's
    (F00-R19), and an annex it cites is on the node (F07-T27): that was checked only by the
    post-merge job, so a skeleton citing an annex that lived in an unmerged pull request passed
    the gate, would merge — by the merge actor, with nobody watching — and then failed the job
    that writes its holes and renders the products. Refused here, where the text is first read
    and before any Lean is built; the post-merge check stays as the backstop for an older pin."""
    from opn_gate import postmerge  # noqa: PLC0415 — postmerge imports the steps

    # F00-T10: a skeleton of an old statement may carry the own-Context import too (the node's
    # directory is named for its id).
    shape_problem = paths.check_proof_is_statement(statement, text, node_id=node_dir.name)
    if shape_problem:
        return shape_problem
    return postmerge.check_annex_citation(node_dir, text)
