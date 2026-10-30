"""F32-T2 (R3; AC3, AC4; Q4, Q5, Q6; D-29 v3.49): a carried proof is checked before the merge.

A partial carrying the proof of one of its holes (``attempts/<name>.<n>.proof``, read at step 2
by T1) has that proof held to the steps a proof of the hole's node meets — D-4 steps 4 to 8 —
against the node exactly as the post-merge job will write it: ``plan_children`` for its id,
``child_proposal`` with the carried witness, ``scaffold.files``, and the ``Proof.lean``
``carried.compose_proof`` makes. Each result is reported in the partial's step of the same
number (Q5: no new step number), so a failure is the partial's, at that step, naming the hole and
the file; step 7's carried-witness check is the child's step 7 and is not run twice. A hole that
is an existing node takes none (Q6).

Over the fake seam; the real staging is ``test_finding_partial_carries_proofs_lean.py``.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest
from fakes import hazards_result, used_constants_result
from harness import TARGET, node_dir
from test_finding_partial_carries_witnesses import (
    BOTH,
    CLOSED,
    GOOD,
    NODE_WITNESS,
    STEM,
    WRONG,
    PerHole,
    carrying,
    holes_report,
    witness_text,
)
from test_partial import ROOT

from opn_gate import carried, layout, pipeline, postmerge, schemas
from opn_gate.steps import hole_proofs
from opn_gate.steps.artifact import ARTIFACT_KEY, Hole
from opn_gate.toolchain import (
    AxiomResult,
    MetaprogramResult,
    ReplayResult,
    ResolvedToolchain,
    UsedConstantsRequest,
)

PROOF = f"{STEM}.1.proof"
CHILD = f"{ROOT}--h1"
CHILD_DECL = CHILD.replace("-", "_")
CHILD_PROOF_MODULE = f"Nodes.«{CHILD}».Proof"
BODY = "by\n  intro p q r h\n  exact h.2\n"
HELPERS = "private theorem pick (p q r : Prop) (h : (p ∧ q) ∧ r) : r :=\n  h.2\n"


def proof_text(hole: str = "right", body: str = BODY, helpers: str = "") -> str:
    return f"-- hole: {hole}\n" + helpers + "-- proof:\n" + body


@dataclass
class Child(PerHole):
    """``PerHole``, answering steps 4, 5 and 8 for the staged child as told."""

    fail_replay_of: str | None = None
    child_axioms: AxiomResult | None = None
    child_constants: MetaprogramResult | None = None
    child_hazards: MetaprogramResult | None = None
    replayed: list[tuple[str, ...]] = field(default_factory=list)

    def kernel_replay(
        self,
        tc: ResolvedToolchain,
        modules: Sequence[str],
        search_path: Sequence[Path],
        *,
        fresh: bool,
        timeout_s: float | None = None,
    ) -> ReplayResult:
        answer = super().kernel_replay(tc, modules, search_path, fresh=fresh, timeout_s=timeout_s)
        self.replayed.append(tuple(modules))
        if self.fail_replay_of is not None and any(self.fail_replay_of in m for m in modules):
            return ReplayResult(ok=False, output="(kernel) declaration type mismatch")
        return answer

    def axioms(
        self,
        tc: ResolvedToolchain,
        module: str,
        decl: str,
        search_path: Sequence[Path],
        scratch: Path,
        *,
        timeout_s: float | None = None,
    ) -> AxiomResult:
        answer = super().axioms(tc, module, decl, search_path, scratch, timeout_s=timeout_s)
        return self.child_axioms if self.child_axioms and "__h" in decl else answer

    def used_constants(
        self,
        tc: ResolvedToolchain,
        req: UsedConstantsRequest,
        search_path: Sequence[Path],
        *,
        timeout_s: float | None = None,
    ) -> MetaprogramResult:
        answer = super().used_constants(tc, req, search_path, timeout_s=timeout_s)
        return self.child_constants if self.child_constants and "__h" in req.decl else answer

    def hazards(self, tc: ResolvedToolchain, req: Any, search_path: Any, **kw: Any) -> Any:
        answer = super().hazards(tc, req, search_path, **kw)
        return self.child_hazards if self.child_hazards and "__h" in req.decl else answer


def carried_proof(tmp_path: Path, files: dict[str, str] | None = None, **kw: Any):  # type: ignore[no-untyped-def]
    """``BOTH``'s two witnesses and a proof of ``right`` (hole 1), on ``test_partial``'s root."""
    fake = kw.pop("fake", None) or Child(witness=NODE_WITNESS)
    return carrying(tmp_path, {**BOTH, PROOF: proof_text(), **(files or {})}, fake=fake, **kw)


# --- AC3: the pass -------------------------------------------------------------------------------


def test_a_carried_proof_is_held_to_steps_4_to_8_against_its_node(tmp_path: Path) -> None:
    """AC3: every step passes; steps 4 to 8 are asked once for the node and once for the staged
    child; the staged child is the writer's output byte for byte; step 4's ``hole-proofs``
    record names the hole, the path and both hashes."""
    ctx, fake = carried_proof(tmp_path)
    verdict = pipeline.run_steps(ctx)
    assert verdict.first_failing_step is None, verdict.as_dict()
    assert [(s.step, s.result) for s in verdict.steps] == [
        (1, "pass"),
        (2, "pass"),
        (4, "pass"),
        (5, "pass"),
        (6, "pass"),
        (7, "pass"),
        (8, "pass"),
    ]
    # Step 4: built and replayed once each.
    assert [m for ms in fake.replayed for m in ms] == [
        f"Nodes.«{ROOT}».Proof",
        CHILD_PROOF_MODULE,
    ]
    assert f"elaborate:{CHILD_PROOF_MODULE}" in fake.calls
    assert f"statement_meaning:{CHILD_PROOF_MODULE}:{CHILD_DECL}" in fake.calls
    # Steps 5 and 8: once each.
    assert [c for c in fake.calls if c.startswith("axioms:")] == [
        f"axioms:Nodes.«{ROOT}».Proof:OpnProp.and_swap_reassoc",
        f"axioms:{CHILD_PROOF_MODULE}:{CHILD_DECL}",
    ]
    assert [c for c in fake.calls if c.startswith("used_constants:")] == [
        "used_constants:OpnProp.and_swap_reassoc",
        f"used_constants:{CHILD_DECL}",
    ]
    # Step 7 (Q5): the node's witness, then each carried witness once — no second check of the
    # proved hole's witness.
    assert [r.decl for r in fake.witness_requests] == [
        "OpnProp.and_swap_reassoc",
        "and_swap_reassoc__h1",
        "and_swap_reassoc__h2",
    ]
    # The staged child is what the writer writes: the same plan, proposal and files, and the
    # composed proof.
    (run,) = ctx.data[hole_proofs.RUNS_KEY]
    assert run.node_id == CHILD and run.hole == "right"
    staged = run.ctx.node.path
    holes = [Hole.of(h) for h in ctx.data[ARTIFACT_KEY]["holes"]]
    proposal = postmerge.child_proposal(
        node_dir(ctx),
        CHILD,
        holes[0],
        author="x",
        origin="x",
        witness=BOTH[f"{STEM}.1.witness"],
        partial_text=(node_dir(ctx) / "attempts" / f"{STEM}.lean").read_text(encoding="utf-8"),
    )
    assert (staged / "Statement.lean").read_text(encoding="utf-8") == proposal.statement
    assert (staged / "Witness.lean").read_text(encoding="utf-8") == proposal.witness
    files = carried.read_file(node_dir(ctx) / "attempts" / PROOF)
    (read,), _ = carried.read_proofs(
        f"attempts/{STEM}.lean", {f"attempts/{PROOF}": files}, ["right"]
    )
    composed = carried.compose_proof(proposal.statement, read)
    assert (staged / "Proof.lean").read_text(encoding="utf-8") == composed
    assert CLOSED["right"] in composed
    # The record, in step 4's passing diagnostic and in ``ctx.data``.
    step4 = next(s for s in verdict.steps if s.step == 4)
    assert step4.diagnostic is not None and step4.diagnostic.code == "hole-proofs"
    entry = {
        "hole": "right",
        "path": f"attempts/{PROOF}",
        "sha256": schemas.content_hash(proof_text().encode("utf-8")),
        "proof_sha256": schemas.content_hash(composed.encode("utf-8")),
        "node": CHILD,
    }
    assert step4.diagnostic.details["proofs"] == [entry]
    # The partial's own facts stay where every reader finds them (graph.partials_of).
    assert step4.diagnostic.details["kind"] == "partial"
    assert step4.diagnostic.details["holes"] == ["right", "left"]
    assert ctx.data[hole_proofs.DATA_KEY] == [entry]
    # Nothing of the child was built in the node's own work directory (step 4's replay and the
    # olean cache read it), nor in the judging directory the partial's verdict rests on.
    assert not (ctx.build_dir / "Nodes" / CHILD).exists()
    assert not str(staged).startswith(str(ctx.workdir) + "/")


def test_the_sub_run_records_its_own_steps(tmp_path: Path) -> None:
    """R5's ``steps its sub-run's``: the child's run carries D-4's list, 1, 2 and 4 to 8, its
    step 7 the carried witness's check (passed), its own step 8's footprint."""
    ctx, _ = carried_proof(tmp_path)
    assert pipeline.run_steps(ctx).first_failing_step is None
    (run,) = ctx.data[hole_proofs.RUNS_KEY]
    assert [(r.step, r.result) for r in run.records] == [
        (1, "pass"),
        (2, "pass"),
        (4, "pass"),
        (5, "pass"),
        (6, "pass"),
        (7, "pass"),
        (8, "pass"),
    ]
    assert run.ctx.data["deps"]["used"] == []
    assert run.ctx.claim.node_id == CHILD
    verdict = run.verdict()
    assert verdict.verdict == "pass" and verdict.first_failing_step is None


def test_a_derived_statements_hazards_are_recorded_not_refused(tmp_path: Path) -> None:
    """R3: step 6 treats the staged node as derived (F07-Q19)."""
    finding = {"checker": "nat-sub", "location": "1:0", "message": "truncated subtraction"}
    fake = Child(witness=NODE_WITNESS, child_hazards=hazards_result([finding]))
    ctx, fake = carried_proof(tmp_path, fake=fake)
    ctx.spec["hazard_checkers"] = ["nat-sub"]
    verdict = pipeline.run_steps(ctx)
    assert verdict.first_failing_step is None, verdict.as_dict()
    assert [c for c in fake.calls if c.startswith("hazards:")] == [
        "hazards:OpnProp.and_swap_reassoc:nat-sub",
        f"hazards:{CHILD_DECL}:nat-sub",
    ]
    (run,) = ctx.data[hole_proofs.RUNS_KEY]
    step6 = next(r for r in run.records if r.step == 6)
    assert step6.diagnostic is not None and step6.diagnostic.code == "hazards-derived-statement"


# --- AC3: each failure is the partial's, at its own step ----------------------------------------


@pytest.mark.parametrize(
    ("fake", "step", "code"),
    [
        (Child(witness=NODE_WITNESS, fail_replay_of=CHILD), 4, "kernel-replay-failed"),
        (
            Child(
                witness=NODE_WITNESS,
                child_axioms=AxiomResult(ok=True, axioms=frozenset({"sorryAx"})),
            ),
            5,
            "axiom-not-allowed",
        ),
        (
            Child(witness=NODE_WITNESS, by_decl={"and_swap_reassoc__h1": WRONG}),
            7,
            "witness-type-mismatch",
        ),
        (
            Child(
                witness=NODE_WITNESS,
                child_constants=used_constants_result(
                    [("OpnProp.and_swap", "Nodes.«tutorial-and-swap».Proof")]
                ),
            ),
            8,
            "undeclared-dependency",
        ),
    ],
)
def test_a_carried_proof_that_fails_refuses_the_partial_at_that_step(
    tmp_path: Path, fake: Child, step: int, code: str
) -> None:
    ctx, _ = carried_proof(tmp_path, fake=fake)
    verdict = pipeline.run_steps(ctx)
    assert verdict.first_failing_step == step, verdict.as_dict()
    assert verdict.diagnostic is not None and verdict.diagnostic.code == code
    assert verdict.diagnostic.details["hole"] == "right"
    assert verdict.diagnostic.details["path"] == f"attempts/{STEM}.1." + (
        "witness" if step == 7 else "proof"
    )
    assert verdict.diagnostic.message.startswith("hole right (")
    assert hole_proofs.DATA_KEY not in ctx.data or step != 4


def test_a_composed_proof_that_does_not_elaborate_fails_step_4(tmp_path: Path) -> None:
    """The child's compile is step 4's; the partial fails there with the child's module named."""

    @dataclass
    class NoChild(Child):
        def elaborate(self, tc: Any, source: Path, module: str, out_dir: Path, **kw: Any) -> Any:
            from opn_gate.toolchain import ElabResult  # noqa: PLC0415

            answer = super().elaborate(tc, source, module, out_dir, **kw)
            if module == CHILD_PROOF_MODULE:
                return ElabResult(ok=False)
            return answer

    ctx, _ = carried_proof(tmp_path, fake=NoChild(witness=NODE_WITNESS))
    verdict = pipeline.run_steps(ctx)
    assert verdict.first_failing_step == 4, verdict.as_dict()
    assert verdict.diagnostic is not None and verdict.diagnostic.code == "elaboration-failed"
    assert verdict.diagnostic.details["module"] == CHILD_PROOF_MODULE
    assert verdict.diagnostic.details["hole"] == "right"


# --- AC4: the refusals ---------------------------------------------------------------------------


def test_refusals(tmp_path: Path) -> None:
    """AC4: unknown, ambiguous, and restated twice — an earlier hole of the node, and a node
    under another branch."""
    # Unknown: a witness and a proof for a hole the assembly does not have.
    ctx, fake = carrying(
        tmp_path / "unknown",
        {
            **BOTH,
            f"{STEM}.3.witness": witness_text("middle"),
            PROOF: proof_text("middle"),
        },
        fake=Child(witness=NODE_WITNESS),
    )
    verdict = pipeline.run_steps(ctx)
    assert verdict.first_failing_step == 4, verdict.as_dict()
    assert verdict.diagnostic is not None and verdict.diagnostic.code == "hole-proof-unknown"
    assert verdict.diagnostic.details == {
        "hole": "middle",
        "path": f"attempts/{PROOF}",
        "holes": ["right", "left"],
    }
    assert [m for ms in fake.replayed for m in ms] == [f"Nodes.«{ROOT}».Proof"]

    # Ambiguous: two holes share the name.
    from fakes import artifact_result  # noqa: PLC0415
    from harness import declared  # noqa: PLC0415
    from test_finding_partial_carries_witnesses import BODY as WBODY  # noqa: PLC0415
    from test_finding_partial_carries_witnesses import STAMP_FILE  # noqa: PLC0415

    report = artifact_result(holes=[("h", CLOSED["right"], False), ("h", CLOSED["left"], False)])
    ctx, _ = carrying(
        tmp_path / "ambiguous",
        {f"{STEM}.1.witness": witness_text("h"), PROOF: proof_text("h")},
        fake=Child(witness=NODE_WITNESS),
        report=report,
    )
    path = node_dir(ctx) / "attempts" / STAMP_FILE
    shared = declared(
        "  intro p q r h\n  have h : r := sorry\n  have h : q ∧ p := sorry\n  exact ⟨h, h⟩\n"
    )
    path.write_text(path.read_text(encoding="utf-8").replace(WBODY, shared), encoding="utf-8")
    verdict = pipeline.run_steps(ctx)
    assert verdict.first_failing_step == 4, verdict.as_dict()
    assert verdict.diagnostic is not None and verdict.diagnostic.code == "hole-proof-ambiguous"
    assert verdict.diagnostic.details["hole"] == "h"

    # Restates an earlier hole of the node: a first decomposition already wrote ``right``'s
    # child, so the plan places this partial's ``right`` on it (R22).
    ctx, _ = carried_proof(tmp_path / "earlier")
    holes = [Hole.of(h) for h in holes_report().doc["holes"]]
    first = postmerge.apply_partial(
        node_dir(ctx), holes[:1], partial_text="", pseudonym="carol", stamp="20260911T000000Z"
    )
    verdict = pipeline.run_steps(ctx)
    assert verdict.first_failing_step == 4, verdict.as_dict()
    assert verdict.diagnostic is not None and verdict.diagnostic.code == "hole-proof-restates"
    assert verdict.diagnostic.details["node"] == first.children[0]
    assert verdict.diagnostic.details["hole"] == "right"

    # Restates a node under another branch: the extractor names it (``defeq_sibling``).
    ctx, _ = carried_proof(
        tmp_path / "lemma", report=holes_report(right={"defeq_sibling": "and-reassoc"})
    )
    verdict = pipeline.run_steps(ctx)
    assert verdict.first_failing_step == 4, verdict.as_dict()
    assert verdict.diagnostic is not None and verdict.diagnostic.code == "hole-proof-restates"
    assert verdict.diagnostic.details["node"] == "and-reassoc"


# --- the old shapes ------------------------------------------------------------------------------


def test_a_partial_carrying_no_proof_is_what_it_was(tmp_path: Path) -> None:
    """R4's last sentence, before the merge: step 4's record is ``artifact-partial`` as it was,
    nothing is staged, and no child is built or replayed."""
    ctx, fake = carrying(tmp_path, BOTH, fake=Child(witness=NODE_WITNESS))
    verdict = pipeline.run_steps(ctx)
    assert verdict.first_failing_step is None
    step4 = next(s for s in verdict.steps if s.step == 4)
    assert step4.diagnostic is not None and step4.diagnostic.code == "artifact-partial"
    assert hole_proofs.DATA_KEY not in ctx.data and hole_proofs.RUNS_KEY not in ctx.data
    assert [m for ms in fake.replayed for m in ms] == [f"Nodes.«{ROOT}».Proof"]
    assert not any(p.name.endswith(hole_proofs.AREA_SUFFIX) for p in ctx.workdir.parent.iterdir())


def test_a_proof_submission_is_untouched(tmp_path: Path) -> None:
    from harness import make_context  # noqa: PLC0415

    ctx = make_context(tmp_path, toolchain=Child())
    verdict = pipeline.run_steps(ctx)
    assert verdict.first_failing_step is None
    assert hole_proofs.RUNS_KEY not in ctx.data


def test_the_grammar_codes_are_still_step_2s(tmp_path: Path) -> None:
    """T1's refusals come first: a proof naming no witnessed hole never reaches step 4."""
    ctx, fake = carrying(
        tmp_path,
        {f"{STEM}.2.witness": BOTH[f"{STEM}.2.witness"], PROOF: proof_text("right")},
        fake=Child(witness=NODE_WITNESS),
    )
    verdict = pipeline.run_steps(ctx)
    assert verdict.first_failing_step == 2
    assert not fake.replayed
    assert layout.node_module(CHILD, "Proof") == CHILD_PROOF_MODULE
    assert GOOD is not None and TARGET
