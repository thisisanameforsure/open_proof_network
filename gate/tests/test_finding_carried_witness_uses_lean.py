"""F07-T54 (R23 with F08-R16, R18), lean tier: a skeleton that declares a definition and a
proved node as uses, and carries the witness of a hole stated over that definition.

erdos-69's shape with a witness on board. The node's statement does not import ``Defs.Twice``;
the skeleton declares it and a proved node's proof, and its hole is stated over ``Opn.twice``.
What only the real toolchain can show: the statement step 7 stages for the hole elaborates
(it needs the declared definition), the carried witness is judged against it, the declared
module is found in the node's build although the staged build comes first on the search path,
and the child the post-merge writer then makes passes the gate's own admission as written.

Lean core only, like the rest of the propositional fixture.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from harness import TARGET
from test_finding_partial_carries_witnesses_lean import admit_as_written
from test_finding_witness_proved_haves_lean import witness_check
from test_uses_defs_lean import context
from test_uses_nodes import TUTORIAL, use_line

from opn_gate import carried, cli, graph, layout, pipeline, postmerge, uses
from opn_gate.paths import Change
from opn_gate.steps.artifact import Hole
from opn_gate.steps.base import RunContext
from opn_gate.toolchain import LocalToolchain

pytestmark = [pytest.mark.lean, pytest.mark.usefixtures("pinned", "lean_pkg")]

NODE = "size-is-id"
CHILD = f"{NODE}--h1"
STEM = "attempts/20261001T000000Z-prover-partial"
SKELETON = f"{STEM}.lean"
#: One hole over the declared definition; the proved node's theorem is in the proof term.
BODY = (
    " by\n"
    "  intro n\n"
    "  have swapped := OpnProp.and_swap True True ⟨trivial, trivial⟩\n"
    "  have key : Opn.twice n = n + n := sorry\n"
    "  rfl\n"
)


def submission(tmp_path: Path, tc: LocalToolchain, witness: str | None) -> tuple[RunContext, str]:
    """The skeleton on ``size-is-id`` with its two use lines, and ``witness`` carried for its
    hole when given: the context and the assembly's text."""
    ctx = context(tmp_path, NODE, tc)
    node = layout.graph_nodes_dir(ctx.graph_root, TARGET) / NODE
    st = layout.parse_statement((node / "Statement.lean").read_text(encoding="utf-8"))
    assert isinstance(st, layout.Statement)
    own = f"import {layout.node_module(NODE, 'Context')}\n"
    text = st.prefix.replace(own, f"{own}import Defs.Twice\n{use_line(TUTORIAL)}\n") + BODY
    (node / SKELETON).write_text(text, encoding="utf-8")
    prefix = f"targets/{TARGET}/nodes/{NODE}/"
    ctx.changes = [Change("A", prefix + SKELETON)]
    if witness is not None:
        name = f"{STEM}.1{carried.SUFFIX}"
        (node / name).write_text(witness, encoding="utf-8")
        ctx.changes.append(Change("A", prefix + name))
    return ctx, text


def test_a_carried_witness_for_a_hole_over_a_declared_definition(
    tmp_path: Path, real_toolchain: LocalToolchain
) -> None:
    ctx, _ = submission(tmp_path / "bare", real_toolchain, None)
    verdict = pipeline.run_submission(ctx)
    assert verdict.verdict == "pass", verdict.as_dict()
    assert verdict.data[uses.USES_KEY]["defs"] == ["Defs.Twice"]
    assert verdict.data[uses.USES_KEY]["nodes"] == [TUTORIAL]
    (reported,) = verdict.data["artifact"]["holes"]
    assert reported["name"] == "key" and "Opn.twice" in reported["closed_type"], reported
    wanted = reported["expected_witness"]
    assert wanted == "∃ (n : Nat), True", reported

    witness = f"-- hole: key\nimport Defs.Twice\n\ntheorem witness : {wanted} := ⟨0, trivial⟩\n"
    ctx, text = submission(tmp_path / "gate", real_toolchain, witness)
    verdict = pipeline.run_submission(ctx)
    assert verdict.verdict == "pass", verdict.as_dict()
    assert [w["hole"] for w in verdict.data[carried.DATA_KEY]] == ["key"]

    node = layout.graph_nodes_dir(ctx.graph_root, TARGET) / NODE
    merged = postmerge.apply_partial(
        node,
        [Hole.of(h) for h in verdict.data["artifact"]["holes"]],
        partial_text=text,
        pseudonym="prover",
        stamp="20261001T000000Z",
        assembly_path=SKELETON,
        witnesses=cli.checked_witnesses(verdict, node),
    )
    assert merged.children == (CHILD,) and merged.witnessed == (CHILD,)
    child = node.parent / CHILD
    statement = (child / "Statement.lean").read_text(encoding="utf-8")
    assert layout.imports_of(statement) == [
        "Defs.Base",
        "Defs.Twice",
        layout.node_module(CHILD, "Context"),
    ]
    staged = ctx.workdir / "holes" / "src" / "Nodes" / CHILD / "Statement.lean"
    assert staged.read_text(encoding="utf-8") == statement
    assert (child / "Witness.lean").read_text(encoding="utf-8") == witness
    admitted = admit_as_written(real_toolchain, tmp_path / "admit", ctx.graph_root, CHILD)
    assert witness_check(admitted) == ("pass", None), admitted.as_dict()
    assert not graph.witness_is_stub(child)
