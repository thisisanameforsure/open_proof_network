"""F08-T24: a proof may use the merged proof of another node of its target (R18, R19; proposed
decisions v3.25; the owner, 2026-10-01: "okay on letting proofs import proved lemma nodes").

Until now a proof could name another node's theorem only if the node was one of its declared
dependencies, and those are fixed when the node is created: a gate-written hole has ``deps: []``,
an authored node keeps the list it was proposed with. So a lemma proved after a node was written
could be used by it only by pasting its proof in (testers 2026-10-01, B1 and B3: six proved
``spec-`` nodes on erdos-69 that no hole could cite, a 75-line lemma duplicated in two sibling
proofs, one lemma planned as twelve pull requests under the heartbeat cap).

A use line ``import Nodes.«<id>».Proof`` declares it, in the artifact's header (``test_uses_defs``
has the header rule). This file pins what makes that sound, with the toolchain faked:

* **what may be named** (step 2): a node of the same target, not this one, not superseded, with
  a merged proof, not already a dependency, and not a node that rests on this one;
* **no cycles**: the last rule over recorded dependencies *and* merged uses, plus the build's
  own chain check; a hole is never proved from the node it was cut from;
* **kernel-extracted truth** (step 8): a declared use the proof term does not make is refused,
  and a node the term uses without declaring is refused as before;
* **the graph** reads a merged proof's use lines as edges: a revision marks a proved user stale,
  the cache builds a used node first, a closure follows uses. Nothing is written for a use.

The real toolchain's half is ``test_uses_nodes_lean.py``. The acceptance tests were seen red
first (``engineering/evidence/F08/task-24-red.txt``).
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml
from fakes import LIBRARY_CONSTANTS, FakeToolchain, artifact_result, used_constants_result
from harness import TARGET, copy_graph, make_context
from test_curator import DATE, NEW_STATEMENT, attest_proved, write_request

from opn_gate import cache, curator, graph, layout, paths, pipeline, products, scaffold, uses
from opn_gate.diagnostic import Diagnostic
from opn_gate.paths import Change
from opn_gate.steps import RunContext, meaning
from opn_gate.steps import stage as staging

TUTORIAL = "tutorial-and-swap"  # proved, no deps
INTERIOR = "and-reassoc"  # proved, no deps, no imports
ROOT = "and-swap-reassoc"  # proved, deps: both of the above


def use_line(node_id: str) -> str:
    return f"import {layout.node_module(node_id, 'Proof')}"


def swap_constant(node_id: str = TUTORIAL) -> tuple[str, str]:
    """A constant of ``node_id``'s proof module, as ``opn-used-constants`` reports one."""
    return ("OpnProp.and_swap", layout.node_module(node_id, "Proof"))


def nodes(ctx: RunContext) -> Path:
    return layout.graph_nodes_dir(ctx.graph_root, TARGET)


def with_uses(ctx: RunContext, *used: str, node_id: str | None = None) -> Path:
    """Rewrite a node's merged proof with one use line per node, where a use line goes: after
    the statement's last import, or leading the file when it has none."""
    path = nodes(ctx) / (node_id or ctx.claim.node_id) / "Proof.lean"
    text = path.read_text(encoding="utf-8")
    lines = "".join(use_line(u) + "\n" for u in used)
    imports = [ln for ln in text.splitlines(keepends=True) if ln.startswith("import ")]
    if imports:
        assert text.count(imports[-1]) == 1
        text = text.replace(imports[-1], imports[-1] + lines)
    else:
        text = lines + text
    path.write_text(text, encoding="utf-8")
    return path


def using(tmp_path: Path, *used: str, node_id: str = INTERIOR, **fake: object) -> RunContext:
    """``node_id`` claimed by a proof that declares ``used``; by default the fake proof term
    uses a constant of each."""
    constants = fake.pop("constants", None)
    toolchain = FakeToolchain(
        constants=used_constants_result(
            [*LIBRARY_CONSTANTS, *(swap_constant(u) for u in used)]
            if constants is None
            else constants  # type: ignore[arg-type]
        ),
        **fake,  # type: ignore[arg-type]
    )
    ctx = make_context(tmp_path, node_id=node_id, toolchain=toolchain)
    with_uses(ctx, *used)
    return ctx


def refused(ctx: RunContext, code: str, step: int = 2) -> Diagnostic:
    verdict = pipeline.run_steps(ctx)
    assert verdict.first_failing_step == step, verdict.as_dict()
    assert verdict.diagnostic is not None and verdict.diagnostic.code == code, verdict.diagnostic
    return verdict.diagnostic


def supersede(ctx: RunContext, node_id: str, successor: str | None) -> None:
    doc = curator.node_status_doc(
        "superseded", "revised (D-8)", author="curator", date=DATE, reference=successor
    )
    path = nodes(ctx) / node_id / "status" / "20260910T121314Z-curator.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")


def add_node(
    ctx: RunContext, node_id: str, *, deps: tuple[str, ...] = (), origin: str = "authored"
) -> Path:
    name = node_id.replace("-", "_")
    return scaffold.write(
        nodes(ctx),
        scaffold.Proposal(
            node_id=node_id,
            target_id=TARGET,
            statement=(
                f"import {layout.node_module(node_id, 'Context')}\n\n"
                f"theorem OpnProp.{name} : ∀ p q : Prop, p ∧ q → q ∧ p := by\n  sorry\n"
            ),
            witness="theorem witness : ∃ p q : Prop, p ∧ q := ⟨True, True, trivial, trivial⟩\n",
            author="curator",
            deps=deps,
            origin=origin,  # type: ignore[arg-type]
            date="2026-10-01T00:00:00Z",
        ),
    )


def prove(ctx: RunContext, node_id: str, *used: str) -> Path:
    """A merged proof for a scaffolded node: its statement with the sorry replaced, and a use
    line for each of ``used``."""
    here = nodes(ctx) / node_id
    st = layout.parse_statement((here / "Statement.lean").read_text(encoding="utf-8"))
    assert isinstance(st, layout.Statement)
    (here / "Proof.lean").write_text(st.prefix + " fun p q h => ⟨h.2, h.1⟩\n", encoding="utf-8")
    if used:
        with_uses(ctx, *used, node_id=node_id)
    return here / "Proof.lean"


# --- the header and the layout --------------------------------------------------------------------


def test_a_node_use_line_is_a_use() -> None:
    statement = layout.parse_statement(
        "import Init\n\ntheorem OpnProp.t : ∀ p : Prop, p → p := by\n  sorry\n"
    )
    assert isinstance(statement, layout.Statement)
    text = statement.prefix.replace(
        "import Init\n", f"import Init\nimport Defs.Extra\n{use_line(TUTORIAL)}\n"
    ) + (" fun _ h => h\n")
    assert paths.check_proof_is_statement(statement, text, node_id="t") is None
    found = uses.declared(statement, text, "t")
    assert found.modules == ("Defs.Extra", layout.node_module(TUTORIAL, "Proof"))
    assert found.nodes == (TUTORIAL,) and found.defs == ("Defs.Extra",)
    assert layout.node_uses(statement, text, "t") == (TUTORIAL,)


@pytest.mark.parametrize("stem", ["Context", "Statement", "Witness", "Relation"])
def test_only_another_nodes_proof_module_is_a_use(stem: str) -> None:
    statement = layout.parse_statement(
        "import Init\n\ntheorem OpnProp.t : ∀ p : Prop, p → p := by\n  sorry\n"
    )
    assert isinstance(statement, layout.Statement)
    line = f"import {layout.node_module(TUTORIAL, stem)}"
    text = statement.prefix.replace("import Init\n", f"import Init\n{line}\n") + " fun _ h => h\n"
    problem = paths.check_proof_is_statement(statement, text, node_id="t")
    assert problem is not None and problem.code == "proof-not-statement"
    assert layout.node_uses(statement, text, "t") == ()


def test_the_layout_takes_a_proof_that_imports_another_nodes_proof(tmp_path: Path) -> None:
    ctx = make_context(tmp_path, node_id=INTERIOR)
    with_uses(ctx, TUTORIAL)
    assert layout.validate_node(nodes(ctx) / INTERIOR) == []


@pytest.mark.parametrize(
    ("file", "module"),
    [
        ("Statement.lean", layout.node_module(TUTORIAL, "Proof")),  # a statement uses nothing
        ("Witness.lean", layout.node_module(TUTORIAL, "Proof")),
        ("Context.lean", layout.node_module(TUTORIAL, "Proof")),
        ("Proof.lean", layout.node_module(TUTORIAL, "Context")),  # only a Proof module
        ("Proof.lean", layout.node_module(INTERIOR, "Proof")),  # never its own
        ("Proof.lean", "Nodes.«tutorial-and-swap».Proof.Extra"),
    ],
)
def test_the_layout_refuses_every_other_node_import(tmp_path: Path, file: str, module: str) -> None:
    ctx = make_context(tmp_path, node_id=INTERIOR)
    path = nodes(ctx) / INTERIOR / file
    path.write_text(f"import {module}\n" + path.read_text(encoding="utf-8"), encoding="utf-8")
    found = layout.check_imports(nodes(ctx) / INTERIOR, INTERIOR)
    assert [d.code for d in found] == ["import-forbidden"], found


def test_a_line_shaped_like_a_use_anywhere_else_is_not_one(tmp_path: Path) -> None:
    """One reading of a use line, for a submission and for the tree alike: where a use line
    stands. The same words inside a comment in the proof's body are no import to Lean, so they
    draw no edge, bring nothing into the build, and the layout refuses them as it did before
    any use existed. Otherwise a proof could *say* it used a node, in a place the kernel never
    reads, and the graph would believe it."""
    ctx = make_context(tmp_path, node_id=INTERIOR)
    proof = nodes(ctx) / INTERIOR / "Proof.lean"
    honest = proof.read_text(encoding="utf-8")
    proof.write_text(honest + f"/-\n{use_line(TUTORIAL)}\n-/\n", encoding="utf-8")
    assert layout.merged_uses(nodes(ctx) / INTERIOR) == ()
    assert uses.edges(nodes(ctx))[INTERIOR] == ()
    assert [d.code for d in layout.check_imports(nodes(ctx) / INTERIOR, INTERIOR)] == [
        "import-forbidden"
    ]
    refused(ctx, "import-forbidden")
    node = layout.load_node(
        nodes(make_context(tmp_path / "b", node_id=INTERIOR)) / INTERIOR, TARGET
    )
    assert isinstance(node, layout.Node)
    (node.path / "Proof.lean").write_text(
        honest + f"/-\n{use_line(TUTORIAL)}\n-/\n", encoding="utf-8"
    )
    assert staging.stage(node, tmp_path / "w").order == (INTERIOR,)


# --- accepted -------------------------------------------------------------------------------------


def test_a_proof_uses_a_proved_node_it_does_not_depend_on(tmp_path: Path) -> None:
    ctx = using(tmp_path, TUTORIAL)
    fake = ctx.toolchain
    assert isinstance(fake, FakeToolchain)
    verdict = pipeline.run_steps(ctx)
    assert verdict.ok, verdict.diagnostic
    assert verdict.data[uses.USES_KEY]["nodes"] == [TUTORIAL]
    # the used node is built before the proof, and the proof is held to the statement's meaning
    used = f"elaborate:{layout.node_module(TUTORIAL, 'Proof')}"
    own = f"elaborate:{layout.node_module(INTERIOR, 'Proof')}"
    assert fake.calls.index(used) < fake.calls.index(own)
    assert verdict.data[meaning.MEANING_KEY]["matches"] is True
    # it reaches the proof through the proof's own import, never through the generated Context
    context = (ctx.workdir / "src" / "Nodes" / INTERIOR / "Context.lean").read_text("utf-8")
    assert "import" not in context.replace("the declared deps", "")
    assert verdict.data["deps"]["used"] == [TUTORIAL]
    assert verdict.data["deps"]["declared"] == []  # the node's recorded deps are what they were
    assert verdict.data["deps"]["uses"]["nodes"] == [TUTORIAL]
    # and nothing about the node itself moved
    here = nodes(ctx) / INTERIOR
    for name in ("Statement.lean", "META.yaml", "Context.lean"):
        fixture = layout.graph_nodes_dir(
            Path(__file__).parent / "fixtures/graphs/propositional", TARGET
        )
        assert (here / name).read_bytes() == (fixture / INTERIOR / name).read_bytes()


def test_a_hole_uses_a_proved_node_of_its_target(tmp_path: Path) -> None:
    """The run's case: a gate-written hole has ``deps: []`` and can cite nothing. It can now
    cite a proved node beside it."""
    fake = FakeToolchain(
        constants=used_constants_result([*LIBRARY_CONSTANTS, swap_constant(INTERIOR)])
    )
    ctx = make_context(tmp_path, node_id=f"{ROOT}--h1", toolchain=fake, changes=[])
    add_node(ctx, f"{ROOT}--h1", origin="compiler-derived")
    prove(ctx, f"{ROOT}--h1", INTERIOR)
    ctx.changes = [Change("A", f"targets/{TARGET}/nodes/{ROOT}--h1/Proof.lean")]
    verdict = pipeline.run_steps(ctx)
    assert verdict.ok, verdict.diagnostic
    assert verdict.data[uses.USES_KEY]["nodes"] == [INTERIOR]


def test_an_alternate_and_a_partial_may_use_a_proved_node(tmp_path: Path) -> None:
    fake = FakeToolchain(
        constants=used_constants_result([*LIBRARY_CONSTANTS, swap_constant(TUTORIAL)])
    )
    ctx = make_context(tmp_path, node_id=INTERIOR, toolchain=fake)
    here = nodes(ctx) / INTERIOR
    text = (here / "Proof.lean").read_text(encoding="utf-8")
    rel = "attempts/20261001T000000Z-prover-alternate.lean"
    (here / rel).write_text(
        use_line(TUTORIAL) + "\n" + text.replace("exact ⟨", "exact id ⟨"), encoding="utf-8"
    )
    ctx.changes = [Change("A", f"targets/{TARGET}/nodes/{INTERIOR}/{rel}")]
    verdict = pipeline.run_steps(ctx)
    assert verdict.ok, verdict.diagnostic
    assert verdict.data[uses.USES_KEY]["nodes"] == [TUTORIAL]

    fake2 = FakeToolchain(
        constants=used_constants_result([*LIBRARY_CONSTANTS, swap_constant(TUTORIAL)]),
        artifact=artifact_result(
            decl="OpnProp.and_reassoc",
            expected="∀ (p q r : Prop), (p ∧ q) ∧ r → p ∧ q ∧ r",
            holes=[("h", "p ∧ q ∧ r", False)],
        ),
    )
    ctx2 = make_context(tmp_path / "partial", node_id=INTERIOR, toolchain=fake2)
    here2 = nodes(ctx2) / INTERIOR
    st = layout.parse_statement((here2 / "Statement.lean").read_text(encoding="utf-8"))
    assert isinstance(st, layout.Statement)
    (here2 / "Proof.lean").unlink()
    rel2 = "attempts/20261001T000000Z-prover-partial.lean"
    (here2 / rel2).write_text(
        use_line(TUTORIAL)
        + "\n"
        + st.prefix
        + " by\n  intro p q r h\n  have h : p ∧ q ∧ r := sorry\n  exact h\n",
        encoding="utf-8",
    )
    ctx2.changes = [Change("A", f"targets/{TARGET}/nodes/{INTERIOR}/{rel2}")]
    verdict2 = pipeline.run_steps(ctx2)
    assert verdict2.ok, verdict2.diagnostic
    # the assembly is staged as the node's Proof module, and its uses are built before it
    assert f"elaborate:{layout.node_module(TUTORIAL, 'Proof')}" in fake2.calls


def test_a_node_without_uses_is_staged_and_checked_as_before(tmp_path: Path) -> None:
    fake = FakeToolchain(
        constants=used_constants_result(
            [*LIBRARY_CONSTANTS, swap_constant(TUTORIAL), swap_constant(INTERIOR)]
        )
    )
    ctx = make_context(tmp_path, node_id=ROOT, toolchain=fake)
    verdict = pipeline.run_steps(ctx)
    assert verdict.ok, verdict.diagnostic
    assert uses.USES_KEY not in verdict.data
    assert "uses" not in verdict.data["deps"]


# --- what may be named (step 2) -------------------------------------------------------------------


def test_a_node_may_not_use_itself(tmp_path: Path) -> None:
    ctx = make_context(tmp_path, node_id=INTERIOR)
    with_uses(ctx, INTERIOR)
    # the layout says it first: a proof never imports its own module
    refused(ctx, "import-forbidden")
    node = layout.load_node(
        nodes(make_context(tmp_path / "b", node_id=INTERIOR)) / INTERIOR, TARGET
    )
    assert isinstance(node, layout.Node)
    problem = uses.check(node, uses.Uses((layout.node_module(INTERIOR, "Proof"),)))
    assert problem is not None and problem.code == "use-self"


def test_a_node_that_does_not_exist_cannot_be_used(tmp_path: Path) -> None:
    ctx = using(tmp_path, "no-such-node")
    assert refused(ctx, "use-unknown-node").details["node"] == "no-such-node"


def test_a_node_with_no_merged_proof_cannot_be_used(tmp_path: Path) -> None:
    """Not proved at the tree being gated: there is nothing to import, and no promise of a
    proof stands in for one."""
    ctx = using(tmp_path, TUTORIAL)
    (nodes(ctx) / TUTORIAL / "Proof.lean").unlink()
    assert refused(ctx, "use-unproved").details["node"] == TUTORIAL


def test_a_submission_cannot_bring_the_proof_it_uses(tmp_path: Path) -> None:
    """The path rule is untouched: a diff that also adds the used node's proof touches two
    nodes and is refused before any use is read."""
    ctx = using(tmp_path, TUTORIAL)
    ctx.changes = [
        Change("M", f"targets/{TARGET}/nodes/{INTERIOR}/Proof.lean"),
        Change("A", f"targets/{TARGET}/nodes/{TUTORIAL}/Proof.lean"),
    ]
    refused(ctx, "path-forbidden")


def test_a_refuted_node_cannot_be_used(tmp_path: Path) -> None:
    ctx = using(tmp_path, TUTORIAL)
    proof = nodes(ctx) / TUTORIAL / "Proof.lean"
    proof.write_text(
        "theorem OpnProp.and_swap_refuted : ¬ (∀ p q : Prop, p ∧ q → q ∧ p) := by\n  sorry\n",
        encoding="utf-8",
    )
    diagnostic = refused(ctx, "use-unproved")
    assert diagnostic.details["artifact"] == "counterexample"


def test_a_superseded_node_cannot_be_used_and_the_refusal_names_its_successor(
    tmp_path: Path,
) -> None:
    ctx = using(tmp_path, TUTORIAL)
    request = write_request(ctx.graph_root, TUTORIAL)
    revised = NEW_STATEMENT.replace("and-reassoc-v2", f"{TUTORIAL}-v2").replace(
        "OpnProp.and_reassoc : ∀ p q r : Prop, (p ∧ q) ∧ r → p ∧ (q ∧ r)",
        "OpnProp.and_swap : ∀ p q : Prop, p ∧ q → q ∧ p",
    )
    curator.revise(ctx.graph_root, TARGET, TUTORIAL, revised, request, author="curator", date=DATE)
    diagnostic = refused(ctx, "use-superseded")
    assert diagnostic.details["successor"] == f"{TUTORIAL}-v2"


def test_a_superseded_node_with_no_sound_successor_is_still_refused(tmp_path: Path) -> None:
    ctx = using(tmp_path, TUTORIAL)
    supersede(ctx, TUTORIAL, "no-such-node")
    assert refused(ctx, "use-superseded").details["successor"] is None


def test_a_dependency_is_not_declared_a_second_time(tmp_path: Path) -> None:
    """One way to name a node: a dependency's theorem reaches the proof through the Context."""
    ctx = using(tmp_path, INTERIOR, node_id=ROOT)
    assert refused(ctx, "use-redundant").details["node"] == INTERIOR


# --- no cycles ------------------------------------------------------------------------------------


def test_a_node_cannot_use_a_node_that_depends_on_it(tmp_path: Path) -> None:
    """``and-swap-reassoc`` declares ``and-reassoc`` as a dependency; a proof of ``and-reassoc``
    that used it would make the two wait on each other."""
    ctx = using(tmp_path, ROOT)
    assert refused(ctx, "use-ancestor").details["node"] == ROOT


def test_a_hole_is_never_proved_from_the_node_it_was_cut_from(tmp_path: Path) -> None:
    """D-12 v3.19 lets a parent be proved directly while its hole stays open. The hole's own
    question is then the parent's again: citing the parent proves nothing new, and the gate
    refuses it however true the parent is."""
    fake = FakeToolchain(constants=used_constants_result([*LIBRARY_CONSTANTS, swap_constant(ROOT)]))
    hole = f"{ROOT}--h1"
    ctx = make_context(tmp_path, node_id=hole, toolchain=fake, changes=[])
    add_node(ctx, hole, origin="compiler-derived")
    meta_path = nodes(ctx) / ROOT / "META.yaml"
    meta = yaml.safe_load(meta_path.read_text(encoding="utf-8"))
    meta["deps"] = [*meta["deps"], hole]  # as the post-merge job records a hole on its parent
    meta_path.write_text(yaml.safe_dump(meta, sort_keys=False), encoding="utf-8")
    prove(ctx, hole, ROOT)
    ctx.changes = [Change("A", f"targets/{TARGET}/nodes/{hole}/Proof.lean")]
    assert refused(ctx, "use-ancestor").details["node"] == ROOT


def test_an_ancestor_reached_through_a_merged_use_is_refused_too(tmp_path: Path) -> None:
    """Laundering: ``lemma``'s merged proof uses the parent; the hole uses ``lemma``. ``lemma``
    is no dependent of the hole by any record, and still rests on it through the parent."""
    fake = FakeToolchain(
        constants=used_constants_result([*LIBRARY_CONSTANTS, swap_constant("lemma")])
    )
    hole = f"{ROOT}--h1"
    ctx = make_context(tmp_path, node_id=hole, toolchain=fake, changes=[])
    add_node(ctx, hole, origin="compiler-derived")
    meta_path = nodes(ctx) / ROOT / "META.yaml"
    meta = yaml.safe_load(meta_path.read_text(encoding="utf-8"))
    meta["deps"] = [*meta["deps"], hole]
    meta_path.write_text(yaml.safe_dump(meta, sort_keys=False), encoding="utf-8")
    add_node(ctx, "lemma")
    prove(ctx, "lemma", ROOT)
    prove(ctx, hole, "lemma")
    ctx.changes = [Change("A", f"targets/{TARGET}/nodes/{hole}/Proof.lean")]
    assert uses.above(nodes(ctx), hole) >= {ROOT, "lemma"}
    assert refused(ctx, "use-ancestor").details["node"] == "lemma"


def test_an_alternate_cannot_use_a_node_whose_proof_uses_this_one(tmp_path: Path) -> None:
    """The one way a user can exist before the proof under check: the node is already proved
    and this is a later proof of it (D-25)."""
    ctx = make_context(tmp_path, node_id=TUTORIAL, toolchain=FakeToolchain())
    add_node(ctx, "lemma")
    prove(ctx, "lemma", TUTORIAL)
    here = nodes(ctx) / TUTORIAL
    text = (here / "Proof.lean").read_text(encoding="utf-8")
    rel = "attempts/20261001T000000Z-prover-alternate.lean"
    (here / rel).write_text(
        use_line("lemma") + "\n" + text.replace("exact ⟨", "exact id ⟨"), encoding="utf-8"
    )
    ctx.changes = [Change("A", f"targets/{TARGET}/nodes/{TUTORIAL}/{rel}")]
    assert refused(ctx, "use-ancestor").details["node"] == "lemma"


def test_a_replaced_hole_is_still_not_proved_from_the_node_it_was_cut_from(tmp_path: Path) -> None:
    """A dependency is read through its revision chain, so once a hole is revised the parent's
    deps *as they are now* name the revision and no longer the old hole. The refusal reads the
    recorded list too: the old hole is still a node the parent was written over."""
    fake = FakeToolchain(constants=used_constants_result([*LIBRARY_CONSTANTS, swap_constant(ROOT)]))
    hole = f"{ROOT}--h1"
    ctx = make_context(tmp_path, node_id=hole, toolchain=fake, changes=[])
    add_node(ctx, hole, origin="compiler-derived")
    successor = f"{ROOT}--h2"  # the node the old hole was replaced by (a consolidation, D-29)
    add_node(ctx, successor, origin="compiler-derived")
    meta_path = nodes(ctx) / ROOT / "META.yaml"
    meta = yaml.safe_load(meta_path.read_text(encoding="utf-8"))
    meta["deps"] = [*meta["deps"], hole]
    meta_path.write_text(yaml.safe_dump(meta, sort_keys=False), encoding="utf-8")
    supersede(ctx, hole, successor)
    assert graph.effective_deps(nodes(ctx), meta["deps"])[-1] == successor
    assert ROOT in uses.above(nodes(ctx), hole) and ROOT in uses.above(nodes(ctx), successor)
    prove(ctx, hole, ROOT)
    ctx.changes = [Change("A", f"targets/{TARGET}/nodes/{hole}/Proof.lean")]
    assert refused(ctx, "use-ancestor").details["node"] == ROOT


def test_a_node_of_another_target_cannot_be_named(tmp_path: Path) -> None:
    """A use line names a node by id, and the id is looked up in the claimed node's own target:
    another target's node is not a node here, whatever it is there."""
    ctx = using(tmp_path, "elsewhere")
    other = ctx.graph_root / "targets" / "another-target" / "nodes" / "elsewhere"
    shutil.copytree(nodes(ctx) / TUTORIAL, other)
    assert refused(ctx, "use-unknown-node").details["node"] == "elsewhere"


def test_an_open_node_has_no_proof_to_use_whatever_else_is_said_of_it(tmp_path: Path) -> None:
    """Unproved covers every open state at once: ready, blocked, speculative, a hole waiting for
    its witness, a hole a circularity claim labels (D-12 v3.35: a label, never a removal). None
    has a merged ``Proof.lean``, and a status is never consulted."""
    ctx = using(tmp_path, "open-lemma")
    add_node(ctx, "open-lemma")
    (nodes(ctx) / "open-lemma" / "attempts").mkdir(exist_ok=True)
    (nodes(ctx) / "open-lemma" / "attempts" / "20261001T000000Z-prover-partial.lean").write_text(
        "theorem OpnProp.open_lemma : ∀ p q : Prop, p ∧ q → q ∧ p := by\n  sorry\n",
        encoding="utf-8",
    )
    assert refused(ctx, "use-unproved").details["artifact"] is None


def test_the_build_refuses_a_cycle_of_uses_whatever_step_2_saw(tmp_path: Path) -> None:
    """The backstop under the rule: two merged proofs that import each other cannot be staged,
    as two modules that import each other cannot be built."""
    ctx = make_context(tmp_path, node_id=INTERIOR)
    with_uses(ctx, TUTORIAL)
    with_uses(ctx, INTERIOR, node_id=TUTORIAL)
    node = layout.load_node(nodes(ctx) / INTERIOR, TARGET)
    assert isinstance(node, layout.Node)
    staged = staging.stage(node, ctx.workdir)
    assert [p.code for p in staged.problems] == ["dep-cycle"]


def test_a_used_nodes_own_uses_are_staged_with_it(tmp_path: Path) -> None:
    """The closure: a dependency whose merged proof uses a third node brings that node into the
    build, deps and uses first."""
    ctx = make_context(tmp_path, node_id=ROOT)
    add_node(ctx, "lemma")
    prove(ctx, "lemma")
    with_uses(ctx, "lemma", node_id=INTERIOR)  # a dependency of the root uses `lemma`
    node = layout.load_node(nodes(ctx) / ROOT, TARGET)
    assert isinstance(node, layout.Node)
    staged = staging.stage(node, ctx.workdir)
    assert staged.problems == ()
    assert staged.order.index("lemma") < staged.order.index(INTERIOR) < staged.order.index(ROOT)
    assert (staged.node_dir("lemma") / "Proof.lean").is_file()


# --- kernel-extracted truth (step 8) --------------------------------------------------------------


def test_a_declared_use_the_proof_term_does_not_make_is_refused(tmp_path: Path) -> None:
    ctx = using(tmp_path, TUTORIAL, constants=LIBRARY_CONSTANTS)
    diagnostic = refused(ctx, "use-unused", step=8)
    assert diagnostic.details["unused"] == [TUTORIAL]


def test_one_use_made_and_one_not_is_refused_for_the_one_not_made(tmp_path: Path) -> None:
    fake = FakeToolchain(constants=used_constants_result([*LIBRARY_CONSTANTS, swap_constant()]))
    ctx = make_context(tmp_path, node_id=INTERIOR, toolchain=fake)
    add_node(ctx, "lemma")
    prove(ctx, "lemma")
    with_uses(ctx, TUTORIAL, "lemma")
    assert refused(ctx, "use-unused", step=8).details["unused"] == ["lemma"]


def test_a_node_reachable_through_a_use_but_not_declared_is_still_refused(tmp_path: Path) -> None:
    """Importing the root's proof makes its dependencies' theorems reachable by name. Reachable
    is not declared: the term names ``tutorial-and-swap``, the header names only ``lemma``."""
    fake = FakeToolchain(
        constants=used_constants_result(
            [*LIBRARY_CONSTANTS, swap_constant("lemma"), swap_constant(TUTORIAL)]
        )
    )
    ctx = make_context(tmp_path, node_id=INTERIOR, toolchain=fake)
    add_node(ctx, "lemma", deps=(TUTORIAL,))
    prove(ctx, "lemma")
    with_uses(ctx, "lemma")
    diagnostic = refused(ctx, "undeclared-dependency", step=8)
    assert diagnostic.details["offences"][0]["node"] == TUTORIAL


def test_a_counterexample_declares_no_use(tmp_path: Path) -> None:
    """Uses are for an artifact that declares the statement's own theorem, which the meaning
    guard can hold to the statement. A counterexample declares another, so its file has no
    place a use line may stand, and the layout refuses the import as it always did."""
    ctx = make_context(tmp_path, node_id=INTERIOR)
    (nodes(ctx) / INTERIOR / "Proof.lean").write_text(
        use_line(TUTORIAL) + "\ntheorem OpnProp.and_reassoc_refuted : "
        "¬ (∀ p q r : Prop, (p ∧ q) ∧ r → p ∧ (q ∧ r)) := by\n  sorry\n",
        encoding="utf-8",
    )
    assert layout.merged_uses(nodes(ctx) / INTERIOR) == ()
    assert refused(ctx, "import-forbidden").details["module"] == layout.node_module(
        TUTORIAL, "Proof"
    )


# --- the graph reads a merged use (R19) -----------------------------------------------------------


def test_a_merged_use_is_a_fact_of_the_tree_and_nothing_is_written_for_it(tmp_path: Path) -> None:
    root = copy_graph(tmp_path)
    ctx = make_context(tmp_path / "ctx", node_id=INTERIOR)
    ctx.graph_root = root
    before = {
        p.relative_to(root): p.read_bytes()
        for p in root.rglob("*")
        if p.is_file() and p.name != "Proof.lean"
    }
    with_uses(ctx, TUTORIAL)
    facts = graph.load_nodes(root, TARGET, [])
    assert facts[INTERIOR].uses == (TUTORIAL,)
    assert facts[INTERIOR].deps == () and facts[INTERIOR].declared_deps == ()
    assert facts[ROOT].uses == () and facts[TUTORIAL].uses == ()
    assert uses.edges(nodes(ctx))[INTERIOR] == (TUTORIAL,)
    after = {
        p.relative_to(root): p.read_bytes()
        for p in root.rglob("*")
        if p.is_file() and p.name != "Proof.lean"
    }
    assert after == before


def test_revising_a_used_node_marks_its_proved_user_stale(tmp_path: Path) -> None:
    """D-8, D-18: a user rests on the node as a dependent does, so the same record marks it,
    and nothing of the user's is rewritten (derive, never rewrite)."""
    root = copy_graph(tmp_path, publish=True)
    ctx = make_context(tmp_path / "ctx", node_id=TUTORIAL)
    ctx.graph_root = root
    with_uses(ctx, INTERIOR, node_id=TUTORIAL)  # the tutorial node's merged proof uses INTERIOR
    attest_proved(root, TUTORIAL, 1)
    attest_proved(root, ROOT, 2)
    meta = (nodes(ctx) / TUTORIAL / "META.yaml").read_bytes()
    proof = (nodes(ctx) / TUTORIAL / "Proof.lean").read_bytes()
    request = write_request(root, INTERIOR)
    revision = curator.revise(
        root, TARGET, INTERIOR, NEW_STATEMENT, request, author="curator", date=DATE
    )
    assert set(revision.dependents) == {ROOT, TUTORIAL}
    tg = graph.load_target(root, TARGET)
    assert tg.statuses[TUTORIAL] == "stale"
    assert (nodes(ctx) / TUTORIAL / "META.yaml").read_bytes() == meta
    assert (nodes(ctx) / TUTORIAL / "Proof.lean").read_bytes() == proof


def test_a_user_with_no_merged_proof_is_not_marked(tmp_path: Path) -> None:
    """A use lives in a merged ``Proof.lean`` or nowhere: an assembly under ``attempts/`` that
    declared one leaves no edge, as it leaves no proof."""
    root = copy_graph(tmp_path)
    here = layout.graph_nodes_dir(root, TARGET) / TUTORIAL
    text = (here / "Proof.lean").read_text(encoding="utf-8")
    (here / "Proof.lean").unlink()
    (here / "attempts" / "20261001T000000Z-prover-partial.lean").write_text(
        use_line(INTERIOR) + "\n" + text, encoding="utf-8"
    )
    assert TUTORIAL not in curator.dependents_of(layout.graph_nodes_dir(root, TARGET), INTERIOR)
    assert graph.load_nodes(root, TARGET, [])[TUTORIAL].uses == ()


def test_the_cache_builds_a_used_node_before_its_user_and_a_closure_follows_uses(
    tmp_path: Path,
) -> None:
    root = copy_graph(tmp_path, publish=True)
    ctx = make_context(tmp_path / "ctx", node_id=TUTORIAL)
    ctx.graph_root = root
    with_uses(ctx, INTERIOR, node_id=TUTORIAL)
    for n, node_id in enumerate((TUTORIAL, INTERIOR, ROOT), start=1):
        attest_proved(root, node_id, n)
    tg = graph.load_target(root, TARGET)
    assert set(tg.statuses.values()) == {"proved"}
    order = cache.proved_order(tg)
    assert order.index(INTERIOR) < order.index(TUTORIAL)
    assert products.dependency_closure(tg, TUTORIAL) == [INTERIOR, TUTORIAL]


def test_the_cache_leaves_out_a_node_whose_used_node_is_not_built(tmp_path: Path) -> None:
    """A user is built only when everything it rests on is: once the used node is revised it is
    no longer ``proved``, the user's import would name a module the cache did not build, and one
    failed module fails the whole cache. So the user is left out, and so is what rests on it."""
    root = copy_graph(tmp_path, publish=True)
    ctx = make_context(tmp_path / "ctx", node_id=TUTORIAL)
    ctx.graph_root = root
    with_uses(ctx, INTERIOR, node_id=TUTORIAL)
    for n, node_id in enumerate((TUTORIAL, INTERIOR, ROOT), start=1):
        attest_proved(root, node_id, n)
    supersede(ctx, INTERIOR, None)
    tg = graph.load_target(root, TARGET)
    assert tg.statuses[INTERIOR] == "superseded" and tg.nodes[TUTORIAL].uses == (INTERIOR,)
    assert cache.proved_order(tg) == []
