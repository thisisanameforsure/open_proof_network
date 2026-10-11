"""D-4 step 7: the non-vacuity witness (F01-R2, R3; Q1).

``Witness.lean`` must exist, elaborate under the pinned toolchain, rest on no axiom outside the
allowlist (in particular not ``sorryAx``), and declare exactly one ``witness`` whose type is
definitionally the expected type the metaprogram derives from ``Statement.lean``.

D-29 v3.22 (F07-T44): for a hole whose ``META.yaml`` records ``proved_binders`` — the binders
of its statement the merged assembly proved — the expected type asks only for the rest, and a
witness of the full type is accepted too. The record is the post-merge job's (``meta/v5``); a
node without it is held to the full type, as every node was before the rule.

F02-T12: nothing of the witness runs in the process that judges it. The statement is built in
the judging directory from the node's own files (``judging.build_statements``); the witness is
compiled in a call of its own, as a module importing that statement in place of its own header
(``judging.with_header``; its own imports must be the statement's, as the elaborating program
required), and ``opn-witness-type`` reads the olean taken from that call as data, mounting the
judging directory read-only and nothing writable.
"""

from __future__ import annotations

import subprocess
from dataclasses import replace
from pathlib import Path
from typing import Any

from opn_gate import carried, judging, layout
from opn_gate.steps.artifact import proved_indices
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

    def run(self, ctx: RunContext) -> StepResult:
        node = ctx.node
        tc: ResolvedToolchain | None = ctx.data.get("toolchain")
        if node is None or tc is None:
            return StepResult.failed("step-order", "step 7 needs steps 1 and 2 to have passed")
        # F02-T12: the node's own files, never the staged copies under the work directory, which
        # the step-4 compile of the contributor's proof could have rewritten.
        node_dir = node.path
        witness_path = node_dir / "Witness.lean"
        if not witness_path.is_file():
            return StepResult.failed("witness-missing", "the node has no Witness.lean")
        req = WitnessRequest(
            statement=node_dir / "Statement.lean",
            statement_module=layout.node_module(node.node_id, "Statement"),
            decl=node.statement.decl_name,
            witness=witness_path,
            witness_module=layout.node_module(node.node_id, "Witness"),
            # D-29 v3.22 (F07-T44): a hole's record of what its assembly proved; none, and the
            # expected type is the full one, as it was for every node before the rule.
            proved=proved_indices(node.meta.get("proved_binders")),
        )
        result, record = judge(
            ctx, tc, req, node_id=node.node_id, context=node.path / "Context.lean"
        )
        if record is not None:
            ctx.data["witness"] = record
        if not result.ok:
            return result
        # F07-R23 (D-29 v3.24): the witnesses a partial carries for its holes, each held to
        # the judgment above against the statement its hole's node will have.
        return check_carried(ctx, tc) or result


def judge(  # noqa: PLR0911 — one return per R2/R3 rule
    ctx: RunContext,
    tc: ResolvedToolchain,
    req: WitnessRequest,
    *,
    node_id: str,
    context: Path,
) -> tuple[StepResult, dict[str, Any] | None]:
    """D-4 step 7's judgment of one witness against one statement (F01-R2, R3): the verdict, and
    the record of what was compared once the metaprogram answered. One function, so a node's own
    witness and a witness a partial carries for a hole (F07-R23) are held to the same rule with
    the same codes. ``req`` names the statement and witness sources and ``context`` the node's
    ``Context.lean`` (the graph's, or the one the gate wrote for a hole); F02-T12: each is
    compiled apart and the program is handed compiled modules only."""
    try:
        result = _judgment(ctx, tc, req, node_id=node_id, context=context)
    except subprocess.TimeoutExpired:
        return StepResult.failed(
            "timeout", f"step 7 exceeded the {ctx.wallclock_s:g}s wall-clock cap"
        ), None
    if isinstance(result, StepResult):
        return result, None
    if not result.ok and not result.doc:
        return metaprogram_failure(WitnessStep.number, result), None
    if not result.ok:
        error = result.error or "witness check failed"
        code = "witness-shape" if "named `witness`" in error else "witness-elaboration"
        return StepResult.failed(
            code,
            error,
            messages=[m.as_dict() for m in result.messages],
            expected=result.doc.get("expected"),
        ), None
    expected = str(result.doc.get("expected"))
    witness_type = result.doc.get("witness")
    axioms = sorted(str(a) for a in result.doc.get("witness_axioms") or [])
    record: dict[str, Any] = {"expected": expected, "witness": witness_type, "axioms": axioms}
    if "sorryAx" in axioms:
        return StepResult.failed(
            "witness-sorry", "Witness.lean depends on sorryAx", axioms=axioms
        ), record
    allowed = set(ctx.spec["axiom_allowlist"])
    outside = [a for a in axioms if a not in allowed]
    if outside:
        return StepResult.failed(
            "witness-axiom",
            f"Witness.lean depends on axioms outside the allowlist: {', '.join(outside)}",
            axioms=outside,
        ), record
    if result.doc.get("defeq") is not True:
        return StepResult.failed(
            "witness-type-mismatch",
            f"witness has type {witness_type} but the statement's hypotheses need {expected}",
            expected=expected,
            witness=witness_type,
        ), record
    return StepResult.passed(), record


def _judgment(
    ctx: RunContext, tc: ResolvedToolchain, req: WitnessRequest, *, node_id: str, context: Path
) -> MetaprogramResult | StepResult:
    """F02-T12: build the statement, compile the witness apart, and ask the program about the
    two compiled modules; a ``StepResult`` when a build fails before there is anything to ask."""
    if req.witness is None or req.witness_module is None:
        return StepResult.failed("witness-missing", "the node has no Witness.lean")
    target_dir = layout.gate_spec_path(ctx.graph_root, ctx.claim.target_id).parent
    where = judging.area(ctx.workdir, f"witness-{node_id}")
    # The node's own statement is built once per run (step 4 built it when it judged the proof);
    # a hole's, from the files the gate wrote for it, here.
    judge = ctx.data.get(judging.KEY)
    node = ctx.node
    if isinstance(judge, judging.Judge) and node is not None and node.node_id == node_id:
        trusted = judge.statement
        problem = judging.node_statement(
            ctx.toolchain, tc, target_dir, node, judge, timeout_s=ctx.wallclock_s
        )
    else:
        trusted = where / judging.STATEMENT_DIR
        problem = judging.build_statements(
            ctx.toolchain,
            tc,
            target_dir,
            [(node_id, context, req.statement)],
            trusted,
            timeout_s=ctx.wallclock_s,
        )
    if problem is not None:
        return StepResult.failed(
            "witness-elaboration",
            f"the statement the witness is checked against does not elaborate: {problem.message}",
            messages=list(problem.details.get("messages") or []),
            expected=None,
        )
    text = req.witness.read_text(encoding="utf-8")
    statement_imports = judging.header_imports(req.statement.read_text(encoding="utf-8"))
    for module in judging.header_imports(text):
        if module not in statement_imports:
            return StepResult.failed(
                "witness-elaboration",
                f"{req.witness}: import {module} is not among the statement's imports",
                messages=[],
                expected=None,
            )
    build = trusted / "build"
    elab, olean = judging.compile_contributed(
        ctx.toolchain,
        tc,
        text=judging.with_header(text, [req.statement_module]),
        module=req.witness_module,
        trusted_build=build,
        where=where,
        timeout_s=ctx.wallclock_s,
    )
    if olean is None:
        return StepResult.failed(
            "witness-elaboration",
            "witness does not elaborate",
            messages=[m.as_dict() for m in elab.errors or elab.messages],
            expected=None,
        )
    reader = judging.confined(ctx.toolchain, read_only=[build, where / judging.CONTRIBUTED_DIR])
    return reader.witness_type(
        tc, replace(req, witness_olean=olean), [build], timeout_s=ctx.wallclock_s
    )


# --- the witnesses a partial carries for its holes (F07-R23; D-29 v3.24) -------------------------

#: Where the would-be children are staged and their Contexts compiled: under the work directory,
#: which the sandbox mounts, and apart from the node's own source and build trees, which step
#: 4's replay and the olean cache read.
HOLES_DIR = "holes"


def check_carried(ctx: RunContext, tc: ResolvedToolchain) -> StepResult | None:  # noqa: PLR0911
    """R23: every witness the partial carries, checked before the merge. ``None`` when the
    submission carries none — a proof, or a partial of the old shape, whose step 7 is the
    node's own and nothing else — or the failure, or the pass that records what was checked.

    Each is the ``Witness.lean`` one hole's node is to be born with, so it is judged against
    that node as the post-merge writer will write it: the same plan, the same proposal, the
    same files (``postmerge.plan_children``, ``child_proposal``, ``scaffold.files``), staged
    under the work directory, with the hole's ``proved_binders`` as the node's META will record
    them (D-29 v3.22). A failure is the partial's, at this step, naming the hole and the file.
    A hole that is an existing node is checked like any other and never written.
    """
    from opn_gate import postmerge, scaffold  # noqa: PLC0415 — both import the steps
    from opn_gate.steps.artifact import ARTIFACT_KEY, PARTIAL_KEY, Hole  # noqa: PLC0415

    partial = ctx.data.get(PARTIAL_KEY)
    node = ctx.node
    if not isinstance(partial, dict) or node is None:
        return None
    files = partial.get(carried.PARTIAL_WITNESSES_KEY)
    if not files:
        return None
    holes = [Hole.of(h) for h in (ctx.data.get(ARTIFACT_KEY) or {}).get("holes") or []]
    names = [h.name for h in holes]
    for entry in files:
        where = {"hole": entry["hole"], "path": entry["path"]}
        if entry["hole"] not in names:
            return StepResult.failed(
                "hole-witness-unknown",
                f"{entry['path']} names the hole {entry['hole']}, and the assembly has no such "
                f"hole; its holes are: {', '.join(names) or 'none'} (F07-R23)",
                **where,
                holes=names,
            )
        if names.count(entry["hole"]) > 1:
            return StepResult.failed(
                "hole-witness-ambiguous",
                f"{entry['path']} names the hole {entry['hole']}, and {names.count(entry['hole'])} "
                "holes of the assembly have that name; give the hole a name of its own to carry "
                "its witness (F07-R23)",
                **where,
            )
    try:
        plan = postmerge.plan_children(node.path, holes)
    except postmerge.GraphWriteError as exc:
        return StepResult.failed("hole-witness-unplaced", str(exc))
    # A hole that is an existing node is staged under the id its position would have had, which
    # nothing else holds (R22: a reused hole's index stays unused), so no staged module can be
    # mistaken for one step 4 built.
    first = postmerge.next_child_index(node.path.parent, node.node_id)
    by_name = {
        hole.name: (hole, postmerge.child_id(node.node_id, first + position), existing)
        for position, (hole, _child, existing) in enumerate(plan)
    }
    src = ctx.workdir / HOLES_DIR / "src"
    build = ctx.workdir / HOLES_DIR / "build"
    # The assembly's own text: its origin, and (F08-R16) the ``Defs.*`` modules it declared as
    # uses, which the writer gives every hole's statement. Without them here the witness was
    # judged against a statement that is not the one written (F07-T54).
    assembly_text = Path(str(partial["file"])).read_text(encoding="utf-8")
    origin = postmerge.child_origin(assembly_text)
    checked: list[dict[str, Any]] = []
    for entry in files:
        hole, staged_id, existing = by_name[entry["hole"]]
        where = {"hole": hole.name, "path": entry["path"]}
        text = carried.read_file(Path(str(entry["file"])))
        try:
            proposal = postmerge.child_proposal(
                node.path,
                staged_id,
                hole,
                author="gate",
                origin=origin,
                witness=text,
                partial_text=assembly_text,
            )
            staged = scaffold.files(node.path.parent, proposal)
        except ValueError as exc:  # scaffold.ScaffoldError: a node that could not be written
            return StepResult.failed("hole-witness-unwritable", f"hole {hole.name}: {exc}", **where)
        dest = src / "Nodes" / staged_id
        dest.mkdir(parents=True, exist_ok=True)
        for name in ("Statement.lean", "Witness.lean", "Context.lean"):
            (dest / name).write_text(staged[name], encoding="utf-8")
        context_module = layout.node_module(staged_id, "Context")
        try:
            elab = ctx.toolchain.elaborate(
                tc,
                dest / "Context.lean",
                context_module,
                build,
                root=src,
                timeout_s=ctx.wallclock_s,
            )
        except subprocess.TimeoutExpired:
            return StepResult.failed(
                "timeout", f"hole {hole.name}: step 7 exceeded the wall-clock cap", **where
            )
        if not elab.ok:
            return StepResult.failed(
                "hole-witness-context",
                f"hole {hole.name}: {context_module} does not elaborate",
                **where,
                messages=[m.as_dict() for m in elab.errors or elab.messages],
            )
        parsed = layout.parse_statement(proposal.statement)
        assert isinstance(parsed, layout.Statement)  # scaffold.files validated it
        req = WitnessRequest(
            statement=dest / "Statement.lean",
            statement_module=layout.node_module(staged_id, "Statement"),
            decl=parsed.decl_name,
            witness=dest / "Witness.lean",
            witness_module=layout.node_module(staged_id, "Witness"),
            proved=hole.proved_binders,
        )
        # The staged build comes first: Lean resolves a module in the first root that has its
        # top-level name, so with the node's build first `Nodes.«child».Context` was looked for
        # there alone and the statement lost its imports (found on the first real-toolchain
        # run). A child's statement imports no node but itself; `Defs.*` is in the node's build.
        result, record = judge(ctx, tc, req, node_id=staged_id, context=dest / "Context.lean")
        if not result.ok:
            assert result.diagnostic is not None
            found = result.diagnostic
            return StepResult.failed(
                found.code,
                f"hole {hole.name} ({entry['path']}): {found.message}",
                **{**found.details, **where},
            )
        checked.append(
            {
                **carried.Carried(hole.name, str(entry["path"]), text).as_dict(),
                **({"node": existing} if existing is not None else {}),
                **(record or {}),
            }
        )
    ctx.data[carried.DATA_KEY] = checked
    return StepResult.passed_with(
        "hole-witnesses",
        f"{len(checked)} of {len(holes)} hole(s) carry a witness, each checked as step 7 checks "
        "a node's (F07-R23)",
        witnesses=[{k: w[k] for k in ("hole", "path", "sha256")} for w in checked],
    )
