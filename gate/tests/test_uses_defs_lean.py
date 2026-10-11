"""F08-T23, lean tier: a declared definition is usable, and cannot change what the statement says
(R16, R17; proposed decisions v3.25).

The fast tier pins the header rule and the wiring (``test_uses_defs.py``). This is the part only
the real toolchain can show, and it is the reason the guard exists: *Lean accepts every trap
below*. Each one is a statement that is false as its own header reads it, a definition module
that changes how the statement's text elaborates, and a "proof" that imports the module and
closes the changed goal. Steps 4 to 8 would all pass it — the module builds, the kernel replays
it, it rests on no axiom — which ``test_without_the_guard_…`` shows by switching the guard off.
With it on, step 4 refuses each as ``statement-meaning-changed``.

Three ways a module can do it are exercised:

* an instance that wins resolution (``Defs.Trap``): same text, another ``Size Nat``;
* a macro on an operator (``Defs.Notation``): ``n + 0`` becomes a product;
* a local definition of the statement's own file whose body resolves differently
  (``OpnProp.sz``): the theorem's type is the same term, the constant under it is not.

Lean core only, like the rest of the propositional fixture.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from harness import TARGET, make_context

from opn_gate import layout, pipeline, scaffold, uses
from opn_gate.paths import Change
from opn_gate.steps import RunContext, meaning
from opn_gate.toolchain import LocalToolchain, ResolvedToolchain

pytestmark = pytest.mark.lean

BASE = (
    "/-! A size, as a class, so that which instance a statement means is a fact of its header. -/\n"
    "\n"
    "namespace Opn\n"
    "\n"
    "class Size (a : Type) where\n"
    "  size : a → Nat\n"
    "\n"
    "instance : Size Nat := ⟨fun n => n⟩\n"
    "\n"
    "end Opn\n"
)
TWICE = "import Defs.Base\n\n/-! Admitted after the statements below. -/\n\n" + (
    "def Opn.twice (n : Nat) : Nat := n + n\n"
)
TRAP = "import Defs.Base\n\ninstance (priority := high) : Opn.Size Nat := ⟨fun _ => 0⟩\n"
NOTATION = "macro_rules | `($a + $b) => `(Nat.mul $a $b)\n"
DEFS = {"Base": BASE, "Twice": TWICE, "Trap": TRAP, "Notation": NOTATION}

WITNESS = "theorem witness : ∃ n : Nat, True := ⟨0, trivial⟩\n"


def statement(node_id: str, body: str, *, imports: tuple[str, ...] = ("Defs.Base",)) -> str:
    header = "".join(f"import {m}\n" for m in (*imports, layout.node_module(node_id, "Context")))
    return header + "\n" + body


#: node id -> its statement. The first is true; the other three are false as stated.
STATEMENTS = {
    "size-is-id": statement(
        "size-is-id",
        "theorem OpnProp.size_is_id : ∀ n : Nat, Opn.Size.size n = n := by\n  sorry\n",
    ),
    "size-is-zero": statement(
        "size-is-zero",
        "theorem OpnProp.size_is_zero : ∀ n : Nat, Opn.Size.size n = 0 := by\n  sorry\n",
    ),
    "plus-zero": statement(
        "plus-zero",
        "theorem OpnProp.plus_zero : ∀ n : Nat, n + 0 = 0 := by\n  sorry\n",
        imports=(),
    ),
    "sz-local": statement(
        "sz-local",
        "def OpnProp.sz (n : Nat) : Nat := Opn.Size.size n\n\n"
        "theorem OpnProp.sz_zero : ∀ n : Nat, OpnProp.sz n = 0 := by\n  sorry\n",
    ),
}


def context(tmp_path: Path, node_id: str, tc: LocalToolchain) -> RunContext:
    """The propositional fixture with the four definitions and four nodes as merged history,
    and ``node_id`` claimed by a submission that adds its ``Proof.lean``."""
    ctx = make_context(
        tmp_path,
        node_id=node_id,
        toolchain=tc,
        changes=[Change("A", f"targets/{TARGET}/nodes/{node_id}/Proof.lean")],
    )
    target_dir = layout.gate_spec_path(ctx.graph_root, TARGET).parent
    for stem, text in DEFS.items():
        (target_dir / "defs" / f"{stem}.lean").write_text(text, encoding="utf-8")
    for other, text in STATEMENTS.items():
        scaffold.write(
            target_dir / "nodes",
            scaffold.Proposal(
                node_id=other,
                target_id=TARGET,
                statement=text,
                witness=WITNESS,
                author="curator",
                date="2026-10-01T00:00:00Z",
            ),
        )
    return ctx


def submit(ctx: RunContext, use: str, body: str) -> None:
    """The node's ``Proof.lean``: its statement, one use line after the own-Context import, and
    ``body`` in place of the ``sorry``."""
    node_id = ctx.claim.node_id
    node = layout.graph_nodes_dir(ctx.graph_root, TARGET) / node_id
    # read from the tree, not from ``STATEMENTS``: a node a test adds (``with_carrier``) is on
    # the tree and must not be written into a module global that the next test's fixture reads
    st = layout.parse_statement((node / "Statement.lean").read_text(encoding="utf-8"))
    assert isinstance(st, layout.Statement)
    own = f"import {layout.node_module(node_id, 'Context')}\n"
    assert st.prefix.count(own) == 1
    text = st.prefix.replace(own, f"{own}import {use}\n") + body
    (node / "Proof.lean").write_text(text, encoding="utf-8")


def test_a_proof_uses_a_definition_its_statement_does_not_import(
    tmp_path: Path, real_toolchain: LocalToolchain, pinned: ResolvedToolchain, lean_pkg: Path
) -> None:
    """R16: every step passes, the definition's constant in the proof term, the statement's own
    module compiled for the comparison and gone again."""
    del pinned, lean_pkg
    ctx = context(tmp_path, "size-is-id", real_toolchain)
    submit(
        ctx,
        "Defs.Twice",
        " by\n  intro n\n  have _h : Opn.twice 1 = 2 := rfl\n  rfl\n",
    )
    verdict = pipeline.run_submission(ctx)
    assert verdict.verdict == "pass", verdict.as_dict()
    assert [(s.step, s.result) for s in verdict.steps] == [
        (n, "pass") for n in (1, 2, 4, 5, 6, 7, 8)
    ]
    assert verdict.data[uses.USES_KEY]["defs"] == ["Defs.Twice"]
    assert verdict.data[meaning.MEANING_KEY] == {"identical": True, "matches": True}
    assert not list((ctx.workdir / "build").rglob("Statement.olean"))


TRAPS = {
    # node, use line, the "proof" Lean accepts under that import
    "instance": ("size-is-zero", "Defs.Trap", " by\n  intro n\n  rfl\n"),
    "notation": ("plus-zero", "Defs.Notation", " by\n  intro n\n  exact Nat.mul_zero n\n"),
    "local-definition": ("sz-local", "Defs.Trap", " by\n  intro n\n  rfl\n"),
}


@pytest.mark.parametrize("trap", sorted(TRAPS))
def test_an_import_that_changes_the_statements_meaning_is_refused(
    tmp_path: Path,
    real_toolchain: LocalToolchain,
    pinned: ResolvedToolchain,
    lean_pkg: Path,
    trap: str,
) -> None:
    """R17: the artifact builds, and step 4 refuses it before any replay. A statement that carries
    a local definition is refused earlier since F08-T37 (D-3 v3.28: a statement holds declarations
    only), at step 2, so that trap never reaches the meaning check; first seen in CI run
    37273045578, restated rather than deleted."""
    del pinned, lean_pkg
    node_id, use, body = TRAPS[trap]
    ctx = context(tmp_path, node_id, real_toolchain)
    submit(ctx, use, body)
    verdict = pipeline.run_submission(ctx)
    assert verdict.verdict == "fail", verdict.as_dict()
    if trap == "local-definition":
        assert verdict.first_failing_step == 2, verdict.as_dict()
        assert verdict.diagnostic is not None
        assert verdict.diagnostic.code == layout.STATEMENT_COMMAND_CODE, verdict.diagnostic
        return
    assert verdict.first_failing_step == 4
    assert verdict.diagnostic is not None
    assert verdict.diagnostic.code == "statement-meaning-changed", verdict.diagnostic
    assert verdict.diagnostic.details["uses"] == [use]
    assert verdict.diagnostic.details["local_mismatch"] == []
    assert verdict.diagnostic.details["expected"] != verdict.diagnostic.details["declared"]


@pytest.mark.parametrize("trap", sorted(TRAPS))
@pytest.mark.usefixtures("pinned", "lean_pkg")
def test_without_the_guard_the_same_proof_passes_every_step(
    tmp_path: Path, real_toolchain: LocalToolchain, trap: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Why the guard is not optional: with it switched off, a false statement is "proved".
    Build, kernel replay, axioms, witness and the dependency check all agree with the trap. The
    local-definition trap is the exception since F08-T37: step 2 refuses its statement whatever
    the guard does, so for it the guard is a second line, not the only one."""
    node_id, use, body = TRAPS[trap]
    ctx = context(tmp_path, node_id, real_toolchain)
    submit(ctx, use, body)
    monkeypatch.setattr(meaning, "guard", lambda *_a, **_k: None)
    verdict = pipeline.run_submission(ctx)
    if trap == "local-definition":
        assert verdict.first_failing_step == 2, verdict.as_dict()
        return
    assert verdict.verdict == "pass", verdict.as_dict()


# --- a partial that declares a definition ---------------------------------------------------------

SKELETON = "attempts/20261001T000000Z-prover-partial.lean"


def submit_partial(ctx: RunContext, use: str, body: str) -> str:
    """One assembly under ``attempts/`` in place of a proof (D-12 #5), with one use line."""
    node_id = ctx.claim.node_id
    st = layout.parse_statement(STATEMENTS[node_id])
    assert isinstance(st, layout.Statement)
    own = f"import {layout.node_module(node_id, 'Context')}\n"
    text = st.prefix.replace(own, f"{own}import {use}\n") + body
    node = layout.graph_nodes_dir(ctx.graph_root, TARGET) / node_id
    (node / SKELETON).write_text(text, encoding="utf-8")
    ctx.changes = [Change("A", f"targets/{TARGET}/nodes/{node_id}/{SKELETON}")]
    return text


def test_a_hole_over_a_declared_definition_becomes_a_statement_that_elaborates(
    tmp_path: Path, real_toolchain: LocalToolchain, pinned: ResolvedToolchain, lean_pkg: Path
) -> None:
    """erdos-69's shape: the node's statement does not import the definition, the skeleton
    declares it, and a hole is stated over it. The gate takes the partial, and the child the
    post-merge job writes imports the definition and elaborates under its own header."""
    from opn_gate import defs, postmerge  # noqa: PLC0415
    from opn_gate.steps import artifact  # noqa: PLC0415

    del lean_pkg
    ctx = context(tmp_path, "size-is-id", real_toolchain)
    text = submit_partial(
        ctx,
        "Defs.Twice",
        " by\n  intro n\n  have key : Opn.twice n = n + n := sorry\n  rfl\n",
    )
    verdict = pipeline.run_submission(ctx)
    assert verdict.verdict == "pass", verdict.as_dict()
    assert verdict.data[uses.USES_KEY]["defs"] == ["Defs.Twice"]
    holes = [artifact.Hole.of(h) for h in verdict.data["artifact"]["holes"]]
    assert [h.name for h in holes] == ["key"]

    node = layout.graph_nodes_dir(ctx.graph_root, TARGET) / "size-is-id"
    merged = postmerge.apply_partial(
        node,
        holes,
        partial_text=text,
        pseudonym="prover",
        stamp="20261001T000000Z",
        assembly_path=SKELETON,
    )
    assert merged.children == ("size-is-id--h1",)
    child = node.parent / "size-is-id--h1"
    statement = (child / "Statement.lean").read_text(encoding="utf-8")
    assert layout.imports_of(statement) == [
        "Defs.Base",
        "Defs.Twice",
        layout.node_module("size-is-id--h1", "Context"),
    ]
    assert layout.validate_node(child) == []

    # the child, built the way the gate builds a node: definitions, its Context, its statement
    work = tmp_path / "child-work"
    target_dir = layout.gate_spec_path(ctx.graph_root, TARGET).parent
    assert defs.compile_all(real_toolchain, pinned, target_dir, work) is None
    staged = work / "src" / "Nodes" / child.name
    staged.mkdir(parents=True)
    for stem in ("Context", "Statement"):
        (staged / f"{stem}.lean").write_text(
            (child / f"{stem}.lean").read_text(encoding="utf-8"), encoding="utf-8"
        )
        elab = real_toolchain.elaborate(
            pinned,
            staged / f"{stem}.lean",
            layout.node_module(child.name, stem),
            work / "build",
            root=work / "src",
        )
        assert elab.ok, (stem, [m.as_dict() for m in elab.messages], elab.stderr)


def test_a_partial_is_held_to_the_statements_meaning_too(
    tmp_path: Path, real_toolchain: LocalToolchain, pinned: ResolvedToolchain, lean_pkg: Path
) -> None:
    """An assembly is a proof of the statement modulo its holes (D-12 #5), so the same guard
    reads it: a skeleton of the false statement, under the instance that makes it true."""
    del pinned, lean_pkg
    ctx = context(tmp_path, "size-is-zero", real_toolchain)
    submit_partial(
        ctx,
        "Defs.Trap",
        " by\n  intro n\n  have key : (0 : Nat) = 0 := sorry\n  exact key ▸ rfl\n",
    )
    verdict = pipeline.run_submission(ctx)
    assert verdict.verdict == "fail", verdict.as_dict()
    assert verdict.first_failing_step == 4
    assert verdict.diagnostic is not None
    assert verdict.diagnostic.code == "statement-meaning-changed", verdict.diagnostic


# --- what a dependency's proof module can carry ---------------------------------------------------

CARRIER = statement("carrier", "theorem OpnProp.carrier : True := by\n  sorry\n")
#: A merged proof of ``carrier`` that step 2 accepts today: the statement with its ``sorry``
#: replaced, and one more command after the body.
CARRIER_PROOF_TAIL = (
    " by\n  trivial\n\ninstance (priority := high) : Opn.Size Nat := ⟨fun _ => 0⟩\n"
)
DEPENDENT = statement(
    "size-is-zero-dep",
    "theorem OpnProp.size_is_zero_dep : ∀ n : Nat, Opn.Size.size n = 0 := by\n  sorry\n",
)


def with_carrier(ctx: RunContext) -> None:
    """``carrier`` proved, its proof module carrying an instance; and a false statement that
    declares it as a dependency."""
    nodes = layout.graph_nodes_dir(ctx.graph_root, TARGET)
    scaffold.write(
        nodes,
        scaffold.Proposal(
            node_id="carrier",
            target_id=TARGET,
            statement=CARRIER,
            witness="theorem witness : True := trivial\n",
            author="curator",
            date="2026-10-01T00:00:00Z",
        ),
    )
    st = layout.parse_statement(CARRIER)
    assert isinstance(st, layout.Statement)
    (nodes / "carrier" / "Proof.lean").write_text(st.prefix + CARRIER_PROOF_TAIL, encoding="utf-8")
    scaffold.write(
        nodes,
        scaffold.Proposal(
            node_id="size-is-zero-dep",
            target_id=TARGET,
            statement=DEPENDENT,
            witness=WITNESS,
            author="curator",
            deps=("carrier",),
            date="2026-10-01T00:00:00Z",
        ),
    )


def test_a_dependencys_proof_module_cannot_change_the_statement_of_an_artifact_with_uses(
    tmp_path: Path, real_toolchain: LocalToolchain, pinned: ResolvedToolchain, lean_pkg: Path
) -> None:
    """The statement is compared as the node's own files read it, with the dependency as a
    signature (D-3's ``Context.lean``), not as the staged build reads it. So an instance that
    arrives through a dependency's merged proof is caught as one arriving through a use is."""
    del pinned, lean_pkg
    ctx = context(tmp_path, "size-is-zero-dep", real_toolchain)
    with_carrier(ctx)
    submit(ctx, "Defs.Twice", " by\n  intro n\n  have _h : Opn.twice 1 = 2 := rfl\n  rfl\n")
    verdict = pipeline.run_submission(ctx)
    assert verdict.verdict == "fail", verdict.as_dict()
    assert verdict.first_failing_step == 4
    assert verdict.diagnostic is not None
    assert verdict.diagnostic.code == "statement-meaning-changed", verdict.diagnostic


def test_a_dependencys_proof_module_cannot_change_the_statement_of_any_artifact(
    tmp_path: Path, real_toolchain: LocalToolchain, pinned: ResolvedToolchain, lean_pkg: Path
) -> None:
    """F08-T28 (Q36): held as a strict xfail until the guard ran for every proof. An artifact
    with no use line anywhere, built on a dependency whose merged proof carries an instance after
    its body (step 2 accepts the file): a false statement passed every step. Refused at step 4."""
    del pinned, lean_pkg
    ctx = context(tmp_path, "size-is-zero-dep", real_toolchain)
    with_carrier(ctx)
    node = layout.graph_nodes_dir(ctx.graph_root, TARGET) / "size-is-zero-dep"
    st = layout.parse_statement(DEPENDENT)
    assert isinstance(st, layout.Statement)
    (node / "Proof.lean").write_text(st.prefix + " by\n  intro n\n  rfl\n", encoding="utf-8")
    verdict = pipeline.run_submission(ctx)
    assert verdict.verdict == "fail", verdict.as_dict()
    assert verdict.first_failing_step == 4
    assert verdict.diagnostic is not None
    assert verdict.diagnostic.code == "statement-meaning-changed", verdict.diagnostic
    assert verdict.diagnostic.details["uses"] == []
    assert verdict.diagnostic.details["carried"] == {}


#: A merged proof of a true statement that carries a macro after its body: from here on ``+`` in
#: every module built on it means ``Nat.mul``. Step 2 accepts the file (prefix and suffix match).
NOTATION_CARRIER = statement(
    "notation-carrier", "theorem OpnProp.notation_carrier : True := by\n  sorry\n"
)
NOTATION_CARRIER_PROOF_TAIL = " by\n  trivial\n\n" + NOTATION
#: False as its own files read it (``n + 0 = 0`` fails at 1), and true once ``+`` is ``Nat.mul``.
NOTATION_DEPENDENT = statement(
    "plus-zero-dep",
    "theorem OpnProp.plus_zero_dep : ∀ n : Nat, n + 0 = 0 := by\n  sorry\n",
    imports=(),
)


def with_notation_carrier(ctx: RunContext) -> None:
    nodes = layout.graph_nodes_dir(ctx.graph_root, TARGET)
    scaffold.write(
        nodes,
        scaffold.Proposal(
            node_id="notation-carrier",
            target_id=TARGET,
            statement=NOTATION_CARRIER,
            witness="theorem witness : True := trivial\n",
            author="curator",
            date="2026-10-01T00:00:00Z",
        ),
    )
    st = layout.parse_statement(NOTATION_CARRIER)
    assert isinstance(st, layout.Statement)
    (nodes / "notation-carrier" / "Proof.lean").write_text(
        st.prefix + NOTATION_CARRIER_PROOF_TAIL, encoding="utf-8"
    )
    scaffold.write(
        nodes,
        scaffold.Proposal(
            node_id="plus-zero-dep",
            target_id=TARGET,
            statement=NOTATION_DEPENDENT,
            witness=WITNESS,
            author="curator",
            deps=("notation-carrier",),
            date="2026-10-01T00:00:00Z",
        ),
    )


def test_a_dependencys_macro_cannot_change_the_statement_of_a_proof_with_no_uses(
    tmp_path: Path, real_toolchain: LocalToolchain, pinned: ResolvedToolchain, lean_pkg: Path
) -> None:
    """F08-T28: the same road with a macro instead of an instance. The dependent declares no use
    and no proof beneath it does; its "proof" closes ``n * 0 = 0``, which is what its statement's
    text reads as once the dependency's module is imported. Refused at step 4."""
    del pinned, lean_pkg
    ctx = context(tmp_path, "plus-zero-dep", real_toolchain)
    with_notation_carrier(ctx)
    node = layout.graph_nodes_dir(ctx.graph_root, TARGET) / "plus-zero-dep"
    st = layout.parse_statement(NOTATION_DEPENDENT)
    assert isinstance(st, layout.Statement)
    (node / "Proof.lean").write_text(
        st.prefix + " by\n  intro n\n  exact Nat.mul_zero n\n", encoding="utf-8"
    )
    verdict = pipeline.run_submission(ctx)
    assert verdict.verdict == "fail", verdict.as_dict()
    assert verdict.first_failing_step == 4
    assert verdict.diagnostic is not None
    assert verdict.diagnostic.code == "statement-meaning-changed", verdict.diagnostic
    assert verdict.diagnostic.details["uses"] == []
    assert verdict.diagnostic.details["carried"] == {}
    assert verdict.diagnostic.details["expected"] != verdict.diagnostic.details["declared"]
