"""F08-T1: mechanical admission and node scaffolding (R1, R4; AC1, AC2, AC3, AC4, AC5).

Against the fake toolchain, so what is under test is the composition — which checks run, in which
order, and what each failure means — rather than Lean's opinion of the files, which
``test_admit_lean.py`` establishes against the real thing.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import samples
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


# --- every remaining refusal, by check (R1, R4; F00-R7: the first failure is named) --------------

from fakes import metaprogram_garbage  # noqa: E402
from scripted import ScriptedToolchain  # noqa: E402

from opn_gate import schemas  # noqa: E402
from opn_gate.steps.base import StepResult  # noqa: E402
from opn_gate.toolchain import MetaprogramResult  # noqa: E402

ROOT_CONTEXT = f"Nodes.«{ROOT_NODE}».Context"


def failure(result: admit.Admission) -> tuple[str | None, str | None]:
    return result.first_failing_check, result.diagnostic.code if result.diagnostic else None


def test_statement_elaboration_failure_is_the_statement_checks(tmp_path: Path) -> None:
    """AC2 sharpened: when Context compiles and only Statement.lean fails, the verdict names the
    statement check with statement-elaboration, and the axiom check never runs."""
    toolchain = ScriptedToolchain(failing_modules={"Nodes.«good».Statement"})
    result = admit.run(context_for(tmp_path, "good", toolchain=toolchain))
    assert failure(result) == ("statement", "statement-elaboration")
    assert result.diagnostic is not None
    assert result.diagnostic.details["module"] == "Nodes.«good».Statement"
    assert not any(c.startswith("axioms:") for c in toolchain.calls)


def test_unreadable_statement_axioms_are_a_refusal(tmp_path: Path) -> None:
    """A statement whose axioms cannot be read is not admitted on the benefit of the doubt."""
    toolchain = FakeToolchain(axiom_result=AxiomResult(ok=False, output="#print axioms: error"))
    result = admit.run(context_for(tmp_path, "good", toolchain=toolchain))
    assert failure(result) == ("statement", "statement-axioms-unreadable")
    assert result.diagnostic is not None
    assert "#print axioms: error" in result.diagnostic.details["output"]


def test_the_wall_clock_cap_is_named_at_each_check(tmp_path: Path) -> None:
    """Contributor Lean runs under the cap at every check that elaborates (C9)."""
    slow_statement = ScriptedToolchain(timeout_modules={"Nodes.«good».Statement"})
    result = admit.run(context_for(tmp_path / "a", "good", toolchain=slow_statement))
    assert failure(result) == ("statement", "timeout")

    slow_axioms = ScriptedToolchain(timeout_on={"axioms"})
    result = admit.run(context_for(tmp_path / "b", "good", toolchain=slow_axioms))
    assert failure(result) == ("statement", "timeout")

    slow_relation = variant_toolchain()
    slow = ScriptedToolchain(witness=slow_relation.witness, timeout_on={"relation_type"})
    result = admit.run(context_for(tmp_path / "c", "variant-resolves", toolchain=slow))
    assert failure(result) == ("relation", "timeout")

    slow_root = ScriptedToolchain(witness=slow_relation.witness, timeout_modules={ROOT_CONTEXT})
    result = admit.run(context_for(tmp_path / "d", "variant-resolves", toolchain=slow_root))
    assert failure(result) == ("relation", "timeout")


def test_checks_run_out_of_order_fail_closed(tmp_path: Path) -> None:
    """Each later check needs what the earlier ones loaded; asked alone, it refuses rather than
    reading nothing and passing."""
    for name, step in admit.default_checks()[2:]:
        ctx = context_for(tmp_path / name, "good")
        result = admit.run(ctx, checks=[(name, step)])
        # Admission's own checks say check-order; the reused D-4 steps say step-order.
        expected = "step-order" if name in ("witness", "hazards") else "check-order"
        assert failure(result) == (name, expected), name
    # And a check that fails without saying why still yields a diagnostic.

    class Silent:
        number = 0
        name = "silent"

        def run(self, ctx: RunContext) -> StepResult:
            return StepResult(ok=False)

    result = admit.run(context_for(tmp_path / "s", "good"), checks=[("silent", Silent())])
    assert failure(result) == ("silent", "failed")
    assert result.as_dict()["checks"] == [
        {"check": "silent", "result": "fail", "diagnostic": result.as_dict()["diagnostic"]}
    ]


# --- the graph check: the target's other nodes are read from META alone --------------------------


def test_a_sibling_without_a_readable_meta_makes_the_graph_unreadable(tmp_path: Path) -> None:
    """The acyclicity question needs every node's deps; a sibling that has no META, or one that
    does not parse, is named rather than skipped (which would hide a cycle)."""
    ctx = context_for(tmp_path, "good")
    (ctx.graph_root / "targets" / TARGET / "nodes" / "stray").mkdir()
    result = admit.run(ctx)
    assert failure(result) == ("graph", "graph-unreadable")
    assert result.diagnostic is not None and "stray has no META.yaml" in result.diagnostic.message

    ctx = context_for(tmp_path / "b", "good")
    meta_path = ctx.graph_root / "targets" / TARGET / "nodes" / ROOT_NODE / "META.yaml"
    meta_path.write_text("deps: [unterminated\n", encoding="utf-8")
    result = admit.run(ctx)
    assert failure(result) == ("graph", "graph-unreadable")


def test_a_sibling_declaring_a_ghost_dep_fails_the_graph_check(tmp_path: Path) -> None:
    """The proposal's own ghost dep is caught at layout; a sibling's is the graph check's."""
    ctx = context_for(tmp_path, "good")
    meta_path = ctx.graph_root / "targets" / TARGET / "nodes" / "and-reassoc" / "META.yaml"
    meta = yaml.safe_load(meta_path.read_text())
    meta["deps"] = ["ghost"]
    meta_path.write_text(yaml.safe_dump(meta, sort_keys=False), encoding="utf-8")
    result = admit.run(ctx)
    assert failure(result) == ("graph", "dep-unknown")
    assert result.diagnostic is not None
    assert result.diagnostic.details == {"node": "and-reassoc", "dep": "ghost"}


def test_a_cycle_among_siblings_is_also_refused(tmp_path: Path) -> None:
    """A proposal cannot be admitted into a graph that is already not a DAG (F03-R3)."""
    ctx = context_for(tmp_path, "good")
    meta_path = ctx.graph_root / "targets" / TARGET / "nodes" / "and-reassoc" / "META.yaml"
    meta = yaml.safe_load(meta_path.read_text())
    meta["deps"] = [ROOT_NODE]
    meta_path.write_text(yaml.safe_dump(meta, sort_keys=False), encoding="utf-8")
    result = admit.run(ctx)
    assert failure(result) == ("graph", "dependency-cycle")
    assert result.diagnostic is not None and "good" not in result.diagnostic.details["cycle"]


def test_dep_edges_reads_every_directory(tmp_path: Path) -> None:
    ctx = context_for(tmp_path, "cycle")
    edges = admit.dep_edges(ctx.graph_root / "targets" / TARGET / "nodes")
    assert edges["cycle"] == (ROOT_NODE,)
    assert edges[ROOT_NODE] == ("tutorial-and-swap", "and-reassoc")
    with pytest.raises(schemas.SchemaError, match=r"has no META\.yaml"):
        (ctx.graph_root / "targets" / TARGET / "nodes" / "empty").mkdir()
        admit.dep_edges(ctx.graph_root / "targets" / TARGET / "nodes")


# --- the relation check: everything between the label and the kernel's answer (R4, D-30) --------


def test_relation_without_a_known_root_is_refused(tmp_path: Path) -> None:
    """A claim relates the variant to the root; with three sinks and no declaration there is no
    root to relate it to, and the proposal is refused rather than related to a guess."""
    ctx = context_for(tmp_path, "variant-resolves", toolchain=variant_toolchain())
    meta_path = ctx.graph_root / "targets" / TARGET / "nodes" / ROOT_NODE / "META.yaml"
    meta = yaml.safe_load(meta_path.read_text())
    meta["deps"] = []
    meta_path.write_text(yaml.safe_dump(meta, sort_keys=False), encoding="utf-8")
    result = admit.run(ctx)
    assert failure(result) == ("relation", "relation-root-unknown")

    # A target-status declaration resolves it (F03-Q5), and so would a rendered graph.json.
    st = ctx.graph_root / "targets" / TARGET / "status"
    st.mkdir()
    (st / "2026-09-10-1.yaml").write_text(
        yaml.safe_dump(samples.target_status(root=ROOT_NODE)), encoding="utf-8"
    )
    assert admit.root_of(ctx.graph_root, TARGET, exclude="variant-resolves") == ROOT_NODE
    ok = admit.run(context_for(tmp_path / "b", "variant-resolves", toolchain=variant_toolchain()))
    assert ok.admitted


def test_root_of_prefers_the_rendered_graph_then_the_declaration(tmp_path: Path) -> None:
    """A rendered graph.json is read only when it validates; then the declaration; then the
    one un-depended-on node — and a graph.json that is not one falls through, never in."""
    from opn_gate import products  # noqa: PLC0415

    ctx = make_context(tmp_path, node_id="good")
    target_dir = ctx.graph_root / "targets" / TARGET
    products.generate(ctx.graph_root, rendered_from=None, commit_time="2026-09-10T00:00:00Z").write(
        ctx.graph_root, write_meta=False
    )
    place(ctx, "good")
    st = target_dir / "status"
    st.mkdir()
    (st / "2026-09-10-1.yaml").write_text(
        yaml.safe_dump(samples.target_status(root="and-reassoc")), encoding="utf-8"
    )
    assert admit.root_of(ctx.graph_root, TARGET) == ROOT_NODE  # the rendered root wins
    (target_dir / "graph.json").write_text('{"root": "tutorial-and-swap"}', encoding="utf-8")
    assert admit.root_of(ctx.graph_root, TARGET) == "and-reassoc"  # no schema: the declaration
    (target_dir / "graph.json").write_text("{broken", encoding="utf-8")
    assert admit.root_of(ctx.graph_root, TARGET) == "and-reassoc"
    (st / "2026-09-10-1.yaml").unlink()
    assert admit.root_of(ctx.graph_root, TARGET, exclude="good") == ROOT_NODE  # the sink
    assert admit.root_of(ctx.graph_root, TARGET) is None  # without the exclusion: two sinks
    assert admit.root_of(ctx.graph_root, "nowhere") is None


def test_an_invalid_root_cannot_be_related_to(tmp_path: Path) -> None:
    ctx = context_for(tmp_path, "variant-resolves", toolchain=variant_toolchain())
    statement = ctx.graph_root / "targets" / TARGET / "nodes" / ROOT_NODE / "Statement.lean"
    statement.write_text(statement.read_text() + "\ntheorem extra : True := by\n  sorry\n")
    result = admit.run(ctx)
    assert failure(result) == ("relation", "relation-root-invalid")
    assert result.diagnostic is not None and ROOT_NODE in result.diagnostic.message


def test_a_root_context_that_does_not_elaborate_is_named(tmp_path: Path) -> None:
    """F08-Q13: the root's Context is staged and compiled for the relation proof; when it does
    not compile the verdict says which module, not merely 'does not elaborate'."""
    toolchain = ScriptedToolchain(
        witness=variant_toolchain().witness, failing_modules={ROOT_CONTEXT}
    )
    result = admit.run(context_for(tmp_path, "variant-resolves", toolchain=toolchain))
    assert failure(result) == ("relation", "relation-root-context")
    assert result.diagnostic is not None and result.diagnostic.details["module"] == ROOT_CONTEXT
    assert not any(c.startswith("relation_type:") for c in toolchain.calls)


def test_relation_must_declare_theorem_relation(tmp_path: Path) -> None:
    """D-30's proof has one name; a file declaring another, or none, is refused before Lean."""
    ctx = context_for(tmp_path, "variant-resolves", toolchain=variant_toolchain())
    relation = ctx.graph_root / "targets" / TARGET / "nodes" / "variant-resolves" / "Relation.lean"
    relation.write_text("-- relation: resolves\ntheorem rel : True := trivial\n")
    result = admit.run(ctx)
    assert failure(result) == ("relation", "relation-decl")
    assert result.diagnostic is not None and result.diagnostic.details["declared"] == "rel"

    ctx = context_for(tmp_path / "b", "variant-resolves", toolchain=variant_toolchain())
    relation = ctx.graph_root / "targets" / TARGET / "nodes" / "variant-resolves" / "Relation.lean"
    relation.write_text("-- relation: resolves\n-- no theorem at all\n")
    result = admit.run(ctx)
    assert failure(result) == ("relation", "artifact-shape")
    assert result.diagnostic is not None and "Relation.lean" in result.diagnostic.message


def test_relation_metaprogram_failures_are_named(tmp_path: Path) -> None:
    garbage = variant_toolchain(relation=metaprogram_garbage(exit_code=2, output="boom"))
    result = admit.run(context_for(tmp_path / "a", "variant-resolves", toolchain=garbage))
    assert failure(result) == ("relation", "metaprogram-failed")
    assert result.diagnostic is not None and result.diagnostic.details["exit_code"] == 2

    broken = MetaprogramResult(ok=False, doc={"ok": False, "error": "type mismatch at relation"})
    result = admit.run(
        context_for(
            tmp_path / "b", "variant-resolves", toolchain=variant_toolchain(relation=broken)
        )
    )
    assert failure(result) == ("relation", "relation-elaboration")
    assert result.diagnostic is not None
    assert result.diagnostic.message == "type mismatch at relation"


def test_a_relation_proof_resting_on_a_foreign_axiom_is_refused(tmp_path: Path) -> None:
    """An implication proved from an axiom outside the allowlist is not the graph's implication."""
    toolchain = variant_toolchain(
        relation=relation_result(label="resolves", expected="V → R", axioms=("Nonsense.ax",))
    )
    result = admit.run(context_for(tmp_path, "variant-resolves", toolchain=toolchain))
    assert failure(result) == ("relation", "relation-axiom")
    assert result.diagnostic is not None and result.diagnostic.details["axioms"] == ["Nonsense.ax"]
    # The allowlist itself is fine.
    allowed = variant_toolchain(
        relation=relation_result(label="resolves", expected="V → R", axioms=("propext",))
    )
    assert admit.run(context_for(tmp_path / "b", "variant-resolves", toolchain=allowed)).admitted


# --- name collisions: a copy of an existing node under a new directory ---------------------------


def test_a_directory_whose_meta_names_another_node_is_refused_at_layout(tmp_path: Path) -> None:
    """A proposal that copies an existing node's files under a new id is not a new node: META's
    id disagrees with the directory, and the layout check says so first."""
    ctx = make_context(tmp_path, node_id="good-copy")
    copy = ctx.graph_root / "targets" / TARGET / "nodes" / "good-copy"
    shutil.copytree(PROPOSALS / "good", copy)
    # Verbatim, the copy's files still import the original's Context: refused for that first.
    result = admit.run(ctx)
    assert failure(result) == ("layout", "import-forbidden")
    # With the imports repointed, what remains is that META names the original.
    for name in ("Statement.lean", "Witness.lean", "Context.lean"):
        text = (copy / name).read_text().replace("«good»", "«good-copy»")
        (copy / name).write_text(text, encoding="utf-8")
    result = admit.run(ctx)
    assert failure(result) == ("layout", "meta-id")
    assert result.diagnostic is not None
    assert "differs from directory 'good-copy'" in result.diagnostic.message
