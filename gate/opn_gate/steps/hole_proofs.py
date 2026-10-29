"""F32-R3 (D-29 v3.49): the proofs a partial carries for its holes, checked before the merge.

A partial may carry, beside its assembly and its holes' witnesses, the proof of a hole
(``attempts/<name>.<n>.proof``; step 2 reads it, ``opn_gate.carried``). The hole has no node yet,
so the proof is held to the steps a proof of that node meets — D-4 steps 2 and 4 to 8 — against
the node exactly as the post-merge job will write it: the id ``postmerge.plan_children`` gives
it, the files ``postmerge.child_proposal`` and ``scaffold.files`` make with the carried witness,
and the ``Proof.lean`` ``carried.compose_proof`` makes from that statement. A failure is the
partial's, at the step of the same number (Q5: the attestation's step list is D-4's), naming the
hole and the file.

**Where each run lives.** Every carried proof is staged as a one-node graph of its own — the
target's ``gate-spec.json`` and ``defs/`` and the child's directory, nothing else — so the proof
can reach the library and the definition modules its statement imports and nothing more (Q4): no
sibling hole, no parent, no other node is there to be named. Each run is a ``RunContext`` over that
graph, with a work directory of its own; both sit in ``<work>.hole-proofs/<child>/``, beside the
partial's work directory and never inside it. The trust boundary is F02-T10's, per run: the
partial's compiles (which run contributor code) are handed the partial's work directory and can
reach no run here; each run's compile of the carried proof is handed that run's work directory
alone (``judging.confined``), so it cannot reach the child's own files the run judges from, nor the
partial's judging directory, nor another carried proof's run; and each run judges in its own
``<work>.judge``, built fresh after its compile, as every gate run does.

**When each runs.** Staging needs the holes, which the partial's step 4 extracts, so the runs are
made at the end of the partial's step 4 (their steps 2 and 4 then); the partial's steps 5, 6 and 8
then run the same step on each (``follow``). Step 7 of a run is the partial's own check of the
hole's carried witness (``witness.check_carried``), which the partial's step 7 has just passed:
it is recorded, not repeated (Q5). Step 6 treats the staged node as derived (F07-Q19), because its
META says so; step 8 finds no declared dependency and no use because the node has none (Q4).
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from opn_gate import carried, judging, layout, schemas
from opn_gate.diagnostic import Diagnostic
from opn_gate.paths import Claim
from opn_gate.steps.base import RunContext, StepResult
from opn_gate.toolchain import ResolvedToolchain

if TYPE_CHECKING:
    from opn_gate.pipeline import StepRecord, Verdict

#: ``ctx.data`` key: what was checked, as plain data — the post-merge writer and the precheck
#: result read it. Set once every step of every run has passed.
DATA_KEY = "hole_proofs"
#: ``ctx.data`` key: each carried proof's own run (``Run``), for the attestations (F32-T3).
RUNS_KEY = "hole_proof_runs"
#: Where each carried proof's run lives, beside the work directory: ``<work>.hole-proofs``.
AREA_SUFFIX = ".hole-proofs"
#: The step a run's step 7 is: the partial's check of the hole's carried witness (Q5).
WITNESS_STEP = 7
#: The last of D-4's steps a run is held to (step 9 is not asked of a hole, F07-Q32).
LAST_STEP = 8


@dataclass
class Run:
    """One carried proof's run against the node its hole becomes."""

    hole: str
    path: str  # the carried file, under the parent node: ``attempts/<name>.<n>.proof``
    sha256: str  # the carried file's bytes
    node_id: str  # the id the writer gives the hole's node
    composed: str  # the node's ``Proof.lean``
    ctx: RunContext
    records: list[StepRecord] = field(default_factory=list)

    @property
    def proof_sha256(self) -> str:
        return schemas.content_hash(self.composed.encode("utf-8"))

    def entry(self) -> dict[str, str]:
        """R3's record of a checked carried proof: hole, path, the file's hash, the composed
        ``Proof.lean``'s hash, and the node it was checked as."""
        return {
            "hole": self.hole,
            "path": self.path,
            "sha256": self.sha256,
            "proof_sha256": self.proof_sha256,
            "node": self.node_id,
        }

    def verdict(self) -> Verdict:
        """The run as a verdict: its steps, and its context's data (F32-T3 attests it)."""
        from opn_gate.pipeline import Verdict  # noqa: PLC0415 — the pipeline imports the steps

        failed = next((r for r in self.records if r.result == "fail"), None)
        return Verdict(
            verdict="pass" if failed is None else "fail",
            steps=tuple(self.records),
            first_failing_step=None if failed is None else failed.step,
            diagnostic=None if failed is None else failed.diagnostic,
            data=dict(self.ctx.data),
        )


def area_for(workdir: Path) -> Path:
    return workdir.parent / f"{workdir.name}{AREA_SUFFIX}"


def _refusal(found: Diagnostic, hole: str, path: str) -> StepResult:
    """A run's failure as the partial's: its code and details, the hole and the file named."""
    return StepResult.failed(
        found.code,
        f"hole {hole} ({path}): {found.message}",
        **{**found.details, "hole": hole, "path": path},
    )


def _record(step: Any, result: StepResult) -> StepRecord:
    from opn_gate.pipeline import StepRecord  # noqa: PLC0415 — the pipeline imports the steps

    return StepRecord(step.number, step.name, "pass" if result.ok else "fail", result.diagnostic)


def _run_step(step: Any, run: Run) -> StepResult:
    """``step`` on one run, an exception being the run's failure (F00-R18), recorded."""
    try:
        result: StepResult = type(step)().run(run.ctx)
    except Exception as exc:  # R18: a step that raises fails, naming the hole
        result = StepResult.failed("unexpected-error", f"{type(exc).__name__}: {exc}")
    run.records.append(_record(step, result))
    return result


def stage(ctx: RunContext, tc: ResolvedToolchain, judged: StepResult) -> StepResult:  # noqa: PLR0911, PLR0912, PLR0915 — one return per R3 rule, in order
    """The end of the partial's step 4: ``judged`` (the artifact check's word) when it failed or
    when nothing is carried; otherwise each carried proof staged, held to steps 2 and 4, and the
    pass recorded as ``hole-proofs`` beside the partial's own facts (``kind``, ``holes``, which
    ``graph.partials_of`` reads), or the first refusal."""
    from opn_gate import postmerge, scaffold  # noqa: PLC0415 — both import the steps
    from opn_gate.steps.artifact import ARTIFACT_KEY, PARTIAL_KEY, Hole  # noqa: PLC0415
    from opn_gate.steps.paths_step import PathsStep  # noqa: PLC0415
    from opn_gate.steps.replay import KernelReplayStep  # noqa: PLC0415

    partial = ctx.data.get(PARTIAL_KEY)
    node = ctx.node
    if not judged.ok or not isinstance(partial, dict) or node is None:
        return judged
    files = partial.get(carried.PARTIAL_PROOFS_KEY)
    if not files:
        return judged
    holes = [Hole.of(h) for h in (ctx.data.get(ARTIFACT_KEY) or {}).get("holes") or []]
    names = [h.name for h in holes]
    for entry in files:
        where = {"hole": entry["hole"], "path": entry["path"]}
        if entry["hole"] not in names:
            return StepResult.failed(
                "hole-proof-unknown",
                f"{entry['path']} names the hole {entry['hole']}, and the assembly has no such "
                f"hole; its holes are: {', '.join(names) or 'none'} (F32-R3)",
                **where,
                holes=names,
            )
        if names.count(entry["hole"]) > 1:
            return StepResult.failed(
                "hole-proof-ambiguous",
                f"{entry['path']} names the hole {entry['hole']}, and {names.count(entry['hole'])} "
                "holes of the assembly have that name; give the hole a name of its own to carry "
                "its proof (F32-R3)",
                **where,
            )
    try:
        plan = postmerge.plan_children(node.path, holes)
    except postmerge.GraphWriteError as exc:
        return StepResult.failed("hole-proof-unplaced", str(exc))
    by_name = {hole.name: (hole, child, existing) for hole, child, existing in plan}
    for entry in files:
        _hole, _child, existing = by_name[entry["hole"]]
        if existing is not None:
            # Q6 (D-12 v3.49): writing Proof.lean into an existing node would be a partial
            # modifying another node (D-3); that node takes a proof through its own submission.
            return StepResult.failed(
                "hole-proof-restates",
                f"{entry['path']} carries a proof of the hole {entry['hole']}, which restates the "
                f"existing node {existing}: no node is created for it, so nothing can be born "
                f"proved. Submit the proof to {existing} as its Proof.lean (F32-R3, Q6)",
                hole=entry["hole"],
                path=entry["path"],
                node=existing,
            )
    witnesses = {
        str(w["hole"]): carried.read_file(Path(str(w["file"])))
        for w in partial.get(carried.PARTIAL_WITNESSES_KEY) or []
    }
    assembly_rel = str(partial["path"])
    assembly_text = Path(str(partial["file"])).read_text(encoding="utf-8")
    origin = postmerge.child_origin(assembly_text)
    area = area_for(ctx.workdir)
    if area.exists():
        shutil.rmtree(area)
    target_dir = layout.gate_spec_path(ctx.graph_root, ctx.claim.target_id).parent
    runs: list[Run] = []
    for entry in files:
        hole, child, _existing = by_name[entry["hole"]]
        assert child is not None  # every existing node was refused above
        path = str(entry["path"])
        text = carried.read_file(Path(str(entry["file"])))
        read, problem = carried.read_proofs(assembly_rel, {path: text}, [hole.name])
        if problem is not None:  # step 2 read the same bytes; a change since is a refusal
            return _refusal(problem, hole.name, path)
        try:
            proposal = postmerge.child_proposal(
                node.path,
                child,
                hole,
                author="gate",
                origin=origin,
                witness=witnesses.get(hole.name),
                partial_text=assembly_text,
            )
            staged = scaffold.files(node.path.parent, proposal)
            composed = carried.compose_proof(proposal.statement, read[0])
        except ValueError as exc:  # scaffold.ScaffoldError, or a statement that does not parse
            return StepResult.failed(
                "hole-proof-unwritable", f"hole {hole.name}: {exc}", hole=hole.name, path=path
            )
        run = Run(
            hole=hole.name,
            path=path,
            sha256=read[0].sha256,
            node_id=child,
            composed=composed,
            ctx=_context(
                ctx,
                tc,
                where=area / child,
                target_dir=target_dir,
                child=child,
                staged=staged,
                composed=composed,
            ),
        )
        run.records.append(_toolchain_record(ctx))
        for step in (PathsStep(), KernelReplayStep()):
            result = _run_step(step, run)
            if not result.ok:
                assert result.diagnostic is not None
                return _refusal(result.diagnostic, hole.name, path)
        runs.append(run)
    ctx.data[RUNS_KEY] = runs
    entries = [r.entry() for r in runs]
    details = dict(judged.diagnostic.details) if judged.diagnostic is not None else {}
    message = judged.diagnostic.message if judged.diagnostic is not None else ""
    return StepResult.passed_with(
        "hole-proofs",
        f"{message}; {len(runs)} hole(s) carry a proof, each built and replayed as the node its "
        "hole becomes (F32-R3)",
        **details,
        proofs=entries,
    )


def _toolchain_record(ctx: RunContext) -> StepRecord:
    """A run's step 1 is the partial's: one toolchain, resolved once."""
    from opn_gate.pipeline import StepRecord  # noqa: PLC0415

    return StepRecord(1, "toolchain", "pass")


def _context(  # noqa: PLR0913 — the run's facts, each named
    ctx: RunContext,
    tc: ResolvedToolchain,
    *,
    where: Path,
    target_dir: Path,
    child: str,
    staged: dict[str, str],
    composed: str,
) -> RunContext:
    """The one-node graph a carried proof is checked in, and its run's context: the target's
    ``gate-spec.json`` and ``defs/`` copied from the graph, the child's files as the writer
    writes them, its ``Proof.lean`` the composed one; a work directory of its own beside it."""
    root = where / "graph"
    target = root / "targets" / ctx.claim.target_id
    target.mkdir(parents=True)
    shutil.copyfile(target_dir / "gate-spec.json", target / "gate-spec.json")
    defs_dir = target_dir / "defs"
    if defs_dir.is_dir():
        shutil.copytree(defs_dir, target / "defs", symlinks=False)
    node_dir = target / "nodes" / child
    for rel, content in staged.items():
        dest = node_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")
    (node_dir / "Proof.lean").write_bytes(composed.encode("utf-8"))
    workdir = where / "work"
    workdir.mkdir(parents=True)
    return RunContext(
        graph_root=root,
        claim=Claim(ctx.claim.target_id, child),
        spec=ctx.spec,
        gate_spec_hash=ctx.gate_spec_hash,
        changes=None,
        workdir=workdir,
        # F02-T10: this run's compile of the carried proof is handed this run's work directory
        # alone, and reads the child's files through it; the run judges from its own.
        toolchain=judging.confined(ctx.toolchain, read_only=[node_dir], read_write=[workdir]),
        settings=ctx.settings,
        data={"toolchain": tc},
    )


def follow(ctx: RunContext, step: Any, result: StepResult) -> StepResult:
    """The partial's step ``step``, then the same step on each carried proof's run (F32-R3); the
    partial's own result when it failed or nothing is carried, else the first run's refusal.
    Step 7 of a run is recorded as the partial's carried-witness check, just passed (Q5). Once
    the last step has passed on every run, ``DATA_KEY`` records what was checked."""
    runs: list[Run] | None = ctx.data.get(RUNS_KEY)
    if not result.ok or not runs:
        return result
    for run in runs:
        if step.number == WITNESS_STEP:
            run.records.append(_record(step, StepResult.passed()))
            continue
        found = _run_step(step, run)
        if not found.ok:
            assert found.diagnostic is not None
            return _refusal(found.diagnostic, run.hole, run.path)
    if step.number == LAST_STEP:
        ctx.data[DATA_KEY] = [r.entry() for r in runs]
    return result
