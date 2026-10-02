"""F07-T54 (R23 with F08-R16): a partial that carries witnesses *and* declares uses.

Two features met at a merge and no test of either covered the meeting. F08-T23 gives a hole of
a partial the ``Defs.*`` modules its assembly declared as uses: the child's statement imports
them, or a hole stated over a definition admitted after the root would not elaborate. F07-T50
checks a carried witness at step 7 against "the statement the post-merge job will write". After
the merge those were two different statements: step 7 staged the child under the parent's
imports alone, and the writer wrote it with the assembly's definitions as well. So a hole over
a declared definition could not carry a witness at all (its staged statement named a definition
it did not import), and a witness that did pass was judged against a file that is not the one
it is born beside.

One function builds the child for both (``postmerge.child_proposal``), and it is given the
assembly; these tests hold the two callers to the same bytes. Over the fake seam; the real
elaboration is ``test_finding_carried_witness_uses_lean.py``.
"""

from __future__ import annotations

from pathlib import Path

from harness import TARGET, node_dir
from test_finding_partial_carries_witnesses import PerHole
from test_uses_defs import USE, partial_context
from test_uses_nodes import TUTORIAL, use_line

from opn_gate import carried, cli, layout, pipeline, postmerge, uses
from opn_gate.paths import Change
from opn_gate.steps.artifact import ARTIFACT_KEY, Hole
from opn_gate.steps.base import RunContext

NODE = "and-reassoc"
CHILD = f"{NODE}--h1"
DECL = "and_reassoc__h1"
STEM = "20261001T000000Z-prover-partial"
WITNESS = "-- hole: h\nimport Defs.Extra\n\ntheorem witness : True := trivial\n"


def carrying(tmp_path: Path, *, node_use: bool = False):  # type: ignore[no-untyped-def]
    """``test_uses_defs``'s partial (one hole, one declared definition), carrying a witness
    for its hole; with ``node_use``, the assembly also declares a proved node."""
    fake = PerHole()
    ctx, rel, text = partial_context(tmp_path, fake)
    here = node_dir(ctx)
    if node_use:
        text = text.replace(f"{USE}\n", f"{USE}\n{use_line(TUTORIAL)}\n")
        (here / rel).write_text(text, encoding="utf-8")
    name = f"attempts/{STEM}.1{carried.SUFFIX}"
    (here / name).write_text(WITNESS, encoding="utf-8")
    assert ctx.changes is not None
    ctx.changes.append(Change("A", f"targets/{TARGET}/nodes/{NODE}/{name}"))
    return ctx, fake, text, rel


def test_step_7_judges_a_carried_witness_against_the_statement_the_writer_writes(
    tmp_path: Path,
) -> None:
    """The statement step 7 staged for the hole imports the definition the assembly declared,
    and is byte for byte the ``Statement.lean`` the post-merge writer then writes; the child is
    born with the witness that was checked."""
    ctx, fake, text, rel = carrying(tmp_path)
    verdict = pipeline.run_steps(ctx)
    assert verdict.first_failing_step is None, verdict.as_dict()
    assert verdict.data[uses.USES_KEY]["defs"] == ["Defs.Extra"]
    assert [w["hole"] for w in verdict.data[carried.DATA_KEY]] == ["h"]
    staged_statement, staged_witness = fake.seen[DECL]
    assert layout.imports_of(staged_statement) == [
        "Defs.Extra",
        layout.node_module(CHILD, "Context"),
    ]
    assert staged_witness == WITNESS

    here = node_dir(ctx)
    merged = postmerge.apply_partial(
        here,
        [Hole.of(h) for h in verdict.data[ARTIFACT_KEY]["holes"]],
        partial_text=text,
        pseudonym="prover",
        stamp="20261001T000000Z",
        assembly_path=rel,
        witnesses=cli.checked_witnesses(verdict, here),
    )
    assert merged.children == (CHILD,) and merged.witnessed == (CHILD,)
    child = here.parent / CHILD
    assert (child / "Statement.lean").read_text(encoding="utf-8") == staged_statement
    assert (child / "Witness.lean").read_text(encoding="utf-8") == WITNESS
    assert layout.validate_node(child) == []


def test_a_node_use_is_the_assemblys_and_not_the_holes(tmp_path: Path) -> None:
    """A use of a proved node is a fact about the assembly's proof term, not about what a hole
    says: the child imports the declared definition and no node's proof, before the merge and
    after it."""
    ctx, fake, text, rel = carrying(tmp_path, node_use=True)
    found = uses.declared(ctx_statement(ctx), text, NODE)
    assert found.defs == ("Defs.Extra",) and found.nodes == (TUTORIAL,)
    here = node_dir(ctx)
    hole = Hole.of({"name": "h", "type": "p ∧ q ∧ r", "closed_type": "True", "synthetic": False})
    before = postmerge.child_proposal(
        here, CHILD, hole, author="gate", origin="authored", witness=WITNESS, partial_text=text
    )
    merged = postmerge.apply_partial(
        here,
        [hole],
        partial_text=text,
        pseudonym="prover",
        stamp="20261001T000000Z",
        assembly_path=rel,
        witnesses={"h": WITNESS},
    )
    assert merged.witnessed == (CHILD,)
    written = (here.parent / CHILD / "Statement.lean").read_text(encoding="utf-8")
    assert written == before.statement
    assert layout.imports_of(written) == ["Defs.Extra", layout.node_module(CHILD, "Context")]
    del fake


def ctx_statement(ctx: RunContext) -> layout.Statement:
    st = layout.parse_statement((node_dir(ctx) / "Statement.lean").read_text(encoding="utf-8"))
    assert isinstance(st, layout.Statement)
    return st


def test_a_partial_with_no_use_lines_stages_what_it_staged(tmp_path: Path) -> None:
    """Nothing changes for a partial that declares no use: the staged child has the parent's
    imports and its own Context, as before."""
    fake = PerHole()
    ctx, rel, text = partial_context(tmp_path, fake)
    here = node_dir(ctx)
    (here / rel).write_text(text.replace(f"{USE}\n", ""), encoding="utf-8")
    name = f"attempts/{STEM}.1{carried.SUFFIX}"
    (here / name).write_text("-- hole: h\n\ntheorem witness : True := trivial\n", encoding="utf-8")
    assert ctx.changes is not None
    ctx.changes.append(Change("A", f"targets/{TARGET}/nodes/{NODE}/{name}"))
    verdict = pipeline.run_steps(ctx)
    assert verdict.first_failing_step is None, verdict.as_dict()
    assert layout.imports_of(fake.seen[DECL][0]) == [layout.node_module(CHILD, "Context")]
