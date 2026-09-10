"""F08-T1: mechanical admission and node scaffolding (R1, R4; AC1, AC2, AC3, AC4, AC5).

Against the fake toolchain, so what is under test is the composition — which checks run, in which
order, and what each failure means — rather than Lean's opinion of the files, which
``test_admit_lean.py`` establishes against the real thing.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml
from fakes import FakeToolchain, hazards_result, relation_result, witness_result
from harness import ADVERSARIAL, GRAPH, TARGET, make_context

from opn_gate import admit, scaffold
from opn_gate.steps.base import RunContext
from opn_gate.toolchain import AxiomResult, ElabResult

PROPOSALS = Path(__file__).resolve().parent / "fixtures" / "proposals"
ROOT_NODE = "and-swap-reassoc"
AUTHOR = "thisisanameforsure"

#: The expected witness type of the fixture variants, as the metaprogram prints it.
VARIANT_WITNESS = "∃ p q r, True"


def place(ctx: RunContext, case: str, *, target: str = TARGET) -> Path:
    """Copy a proposal fixture into the graph the context is over, as a PR would add it."""
    dest = ctx.graph_root / "targets" / target / "nodes" / case
    shutil.copytree(PROPOSALS / case, dest)
    return dest


def context_for(
    tmp_path: Path, case: str, *, toolchain: FakeToolchain | None = None, graph: Path = GRAPH
) -> RunContext:
    target = "adversarial" if graph is ADVERSARIAL else TARGET
    ctx = make_context(
        tmp_path, node_id=case, toolchain=toolchain or FakeToolchain(), graph=graph, target=target
    )
    place(ctx, case, target=target)
    return ctx


def names(result: admit.Admission) -> list[tuple[str, str]]:
    return [(c.name, c.result) for c in result.checks]


# --- AC1: a well-formed proposal passes every check, in R1's order -------------------------------


def test_admission_order_and_pass(tmp_path: Path) -> None:
    """AC1: every check passes, in the order R1 fixes, and the verdict says so."""
    good_witness = witness_result(expected="∃ p q, p ∧ q", witness="∃ p q, p ∧ q")
    toolchain = FakeToolchain(witness=good_witness)
    ctx = context_for(tmp_path, "good", toolchain=toolchain)
    result = admit.run(ctx)
    assert result.admitted, result.as_dict()
    assert [c.name for c in result.checks] == [
        "toolchain",
        "layout",
        "statement",
        "witness",
        "hazards",
        "context",
        "graph",
        "relation",
    ]
    assert {c.result for c in result.checks} == {"pass"}
    assert result.first_failing_check is None
    assert result.as_dict()["verdict"] == "pass"


# --- AC2: the first failure is the useful one, and nothing after it runs -------------------------


def test_typecheck_first(tmp_path: Path) -> None:
    """AC2: a statement that does not elaborate fails at the statement check; later ones skip."""
    toolchain = FakeToolchain(elab=ElabResult(ok=False))
    ctx = context_for(tmp_path, "bad-statement", toolchain=toolchain)
    result = admit.run(ctx)
    assert not result.admitted
    # The layout check compiles Context.lean first, so a failing elaboration stops there; either
    # way the verdict names an elaboration failure and nothing after it runs.
    assert result.first_failing_check in ("layout", "statement")
    assert result.diagnostic is not None
    assert "elaborat" in result.diagnostic.message
    after = names(result)[[c.name for c in result.checks].index(result.first_failing_check) + 1 :]
    assert {r for _, r in after} == {"skipped"}


def test_statement_axioms_outside_the_allowlist(tmp_path: Path) -> None:
    """R1: a statement may rest on its own sorry and the allowlist, and on nothing else."""
    toolchain = FakeToolchain(
        axiom_result=AxiomResult(ok=True, axioms=frozenset({"sorryAx", "Nonsense.ax"}))
    )
    ctx = context_for(tmp_path, "good", toolchain=toolchain)
    result = admit.run(ctx)
    assert result.first_failing_check == "statement"
    assert result.diagnostic is not None and result.diagnostic.code == "statement-axiom"
    assert result.diagnostic.details["axioms"] == ["Nonsense.ax"]

    # sorryAx alone is exactly what a statement is supposed to rest on.
    ok = FakeToolchain(axiom_result=AxiomResult(ok=True, axioms=frozenset({"sorryAx"})))
    assert admit.run(context_for(tmp_path / "b", "good", toolchain=ok)).admitted


def test_bad_witness_fails_at_the_witness_check(tmp_path: Path) -> None:
    """R1: F01's step 7, unchanged, asked of a node that has no proof yet."""
    toolchain = FakeToolchain(
        witness=witness_result(expected="∃ p q, p ∧ q", witness="∃ p, p", defeq=False)
    )
    ctx = context_for(tmp_path, "bad-witness", toolchain=toolchain)
    result = admit.run(ctx)
    assert result.first_failing_check == "witness"
    assert result.diagnostic is not None and result.diagnostic.code == "witness-type-mismatch"


def test_unacknowledged_hazard_fails(tmp_path: Path) -> None:
    """R1: F02's step 6, unchanged. The adversarial graph is the one with checkers enabled."""
    finding = {
        "checker": "nat-sub",
        "location": "n - 1",
        "message": "truncated subtraction on Nat",
    }
    toolchain = FakeToolchain(hazards_doc=hazards_result([finding], checkers=["nat-sub"]))
    ctx = context_for(tmp_path, "hazard", toolchain=toolchain, graph=ADVERSARIAL)
    result = admit.run(ctx)
    assert result.first_failing_check == "hazards"
    assert result.diagnostic is not None and result.diagnostic.code == "hazard-unacknowledged"


# --- AC3: the graph stays a graph ----------------------------------------------------------------


def test_cycle_rejected(tmp_path: Path) -> None:
    """AC3: a proposal that closes a loop is refused, naming the cycle."""
    ctx = context_for(tmp_path, "cycle")
    # The fixture depends on the root; make the root depend back, which is the only way a new
    # node can create a cycle — its own deps all point at nodes that already exist.
    meta_path = ctx.graph_root / "targets" / TARGET / "nodes" / ROOT_NODE / "META.yaml"
    meta = yaml.safe_load(meta_path.read_text())
    meta["deps"] = [*meta["deps"], "cycle"]
    meta_path.write_text(yaml.safe_dump(meta, sort_keys=False), encoding="utf-8")

    result = admit.run(ctx)
    assert result.first_failing_check == "graph"
    assert result.diagnostic is not None and result.diagnostic.code == "dependency-cycle"
    assert "cycle" in result.diagnostic.details["cycle"]
    assert ROOT_NODE in result.diagnostic.details["cycle"]


def test_unknown_dep_rejected(tmp_path: Path) -> None:
    """R1: a declared dep that is not a node of the target is named, not silently ignored."""
    ctx = context_for(tmp_path, "cycle")
    meta_path = ctx.graph_root / "targets" / TARGET / "nodes" / "cycle" / "META.yaml"
    meta = yaml.safe_load(meta_path.read_text())
    meta["deps"] = ["ghost"]
    meta_path.write_text(yaml.safe_dump(meta, sort_keys=False), encoding="utf-8")
    result = admit.run(ctx)
    # `layout.load_node` refuses a dep that is not a directory before the graph check is reached.
    assert result.first_failing_check == "layout"
    assert result.diagnostic is not None and "ghost" in str(result.diagnostic.details)


# --- AC4, AC5: D-30's labels are claims, and a claim is proved -----------------------------------


def variant_toolchain(**overrides: object) -> FakeToolchain:
    return FakeToolchain(
        witness=witness_result(expected=VARIANT_WITNESS, witness=VARIANT_WITNESS),
        **overrides,  # type: ignore[arg-type]
    )


def test_relation_direction(tmp_path: Path) -> None:
    """AC4: the wrong direction fails naming both types; the right one passes."""
    expected = "V → R"
    backwards = variant_toolchain(
        relation=relation_result(label="partial", expected="R → V", declared=expected)
    )
    ctx = context_for(tmp_path, "variant-backwards", toolchain=backwards)
    result = admit.run(ctx)
    assert result.first_failing_check == "relation"
    assert result.diagnostic is not None and result.diagnostic.code == "relation-direction"
    assert result.diagnostic.details["expected"] == "R → V"
    assert result.diagnostic.details["declared"] == expected

    right = variant_toolchain(relation=relation_result(label="resolves", expected=expected))
    ok = admit.run(context_for(tmp_path / "b", "variant-resolves", toolchain=right))
    assert ok.admitted, ok.as_dict()
    assert ok.data["relation"]["label"] == "resolves"


def test_relation_required_above_related(tmp_path: Path) -> None:
    """AC5: ``related`` needs no proof and passes; a label above it cannot be made without one."""
    related = admit.run(context_for(tmp_path, "variant-related", toolchain=variant_toolchain()))
    assert related.admitted, related.as_dict()
    assert related.data["relation_label"] == "related"

    # The label lives in Relation.lean's `-- relation:` line (F03's convention), so claiming
    # `partial` with no proof is not a node anyone can build: the scaffold refuses it first.
    with pytest.raises(scaffold.ScaffoldError, match="relation proof"):
        scaffold.files(
            GRAPH / "targets" / TARGET / "nodes",
            scaffold.Proposal(
                node_id="claim-only",
                target_id=TARGET,
                statement="theorem t : True := by\n  sorry\n",
                witness="theorem witness : True := trivial\n",
                author=AUTHOR,
                origin="variant",
                relation="partial",
            ),
        )


def test_a_relation_proof_that_claims_nothing_is_refused(tmp_path: Path) -> None:
    """D-30: a Relation.lean with no label claims nothing, so it has no business existing."""
    ctx = context_for(tmp_path, "variant-related", toolchain=variant_toolchain())
    node_dir = ctx.graph_root / "targets" / TARGET / "nodes" / "variant-related"
    (node_dir / "Relation.lean").write_text("theorem relation : True := trivial\n")
    result = admit.run(ctx)
    assert result.first_failing_check == "relation"
    assert result.diagnostic is not None and result.diagnostic.code == "relation-unlabelled"


def test_relation_on_a_non_variant_is_refused(tmp_path: Path) -> None:
    """D-3: Relation.lean is a variant's file and nobody else's."""
    ctx = context_for(tmp_path, "good")
    node_dir = ctx.graph_root / "targets" / TARGET / "nodes" / "good"
    labelled = "-- relation: resolves\ntheorem relation : True := trivial\n"
    (node_dir / "Relation.lean").write_text(labelled)
    result = admit.run(ctx)
    assert result.first_failing_check == "relation"
    assert result.diagnostic is not None and result.diagnostic.code == "relation-not-a-variant"


def test_a_sorry_in_the_relation_proof_is_refused(tmp_path: Path) -> None:
    """D-30: the implication is proved or it is not claimed."""
    toolchain = variant_toolchain(
        relation=relation_result(label="resolves", expected="V → R", axioms=("sorryAx",))
    )
    result = admit.run(context_for(tmp_path, "variant-resolves", toolchain=toolchain))
    assert result.first_failing_check == "relation"
    assert result.diagnostic is not None and result.diagnostic.code == "relation-sorry"


# --- a check that raises is that check's failure, never a crash ----------------------------------


def test_an_exploding_check_is_a_verdict(tmp_path: Path) -> None:
    """C7, F00-R18: admission runs on contributor files and always produces a verdict."""
    toolchain = FakeToolchain(raise_on="witness_type")
    result = admit.run(context_for(tmp_path, "good", toolchain=toolchain))
    assert not result.admitted
    assert result.first_failing_check == "witness"
    assert result.diagnostic is not None and result.diagnostic.code == "unexpected-error"
