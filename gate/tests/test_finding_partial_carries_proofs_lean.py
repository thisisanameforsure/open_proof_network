"""F32-T2 (R3, AC5; Q4; D-29 v3.49), lean tier: a carried proof through the real toolchain.

The fast tier (``test_finding_partial_carries_proofs.py``) shows the plumbing over the fake seam,
which cannot see what Lean sees: whether the ``Proof.lean`` the gate composes for a hole that
does not exist yet elaborates as that hole's node, with a helper before it; and whether the
one-node graph it is staged in really keeps the proof away from everything Q4 puts out of reach
— the sibling hole, the parent, and a definition module the hole's statement does not import.
Each of those names an existing constant somewhere in the target; staged as the gate stages it,
none is there, and the partial is refused at step 4 with nothing merged.

The flow a contributor follows: precheck the bare skeleton, read each hole's expected witness
type, carry a witness of it for both holes and a proof of one.

Lean core only, like the rest of the propositional fixture, plus two definition modules.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from harness import TARGET, declared, make_context

from opn_gate import carried, layout, pipeline, scaffold
from opn_gate.paths import Change
from opn_gate.steps import hole_proofs
from opn_gate.steps.base import RunContext
from opn_gate.toolchain import LocalToolchain

pytestmark = [pytest.mark.lean, pytest.mark.usefixtures("pinned", "lean_pkg")]

NODE = "doubling"
DECL = "OpnProp.doubling"
STEM = "attempts/20261029T000000Z-prover-partial"
SKELETON = f"{STEM}.lean"
DOUBLE = (
    "/-! Doubling, as a definition the statements are stated over. -/\n\n"
    "def Opn.double (n : Nat) : Nat := n + n\n"
)
#: A lemma about ``Opn.double`` in a module the hole's statement does not import.
OTHER = "import Defs.Double\n\ntheorem Opn.double_def (n : Nat) : Opn.double n = n + n := rfl\n"
STATEMENT = (
    "import Defs.Double\n"
    f"import {layout.node_module(NODE, 'Context')}\n"
    "\n"
    f"theorem {DECL} : ∀ n : Nat, Opn.double n = n + n ∧ n + 0 = n := by\n"
    "  sorry\n"
)
BODY = declared(
    " by\n"
    "  intro n\n"
    "  have first : Opn.double n = n + n := sorry\n"
    "  have second : n + 0 = n := sorry\n"
    "  exact ⟨first, second⟩\n"
)
HELPER = "private theorem unfold_double (n : Nat) : Opn.double n = n + n := rfl\n"
GOOD = f"-- hole: first\n{HELPER}-- proof:\nby\n  intro n\n  exact unfold_double n\n"
CHILD = f"{NODE}--h1"


def context(tmp_path: Path, tc: LocalToolchain) -> RunContext:
    """The propositional fixture with ``Defs.Double``, ``Defs.Other`` and the node ``doubling``
    (stated over ``Opn.double``) as merged history; nothing claimed yet."""
    ctx = make_context(tmp_path, node_id=NODE, toolchain=tc, changes=[])
    target_dir = layout.gate_spec_path(ctx.graph_root, TARGET).parent
    (target_dir / "defs" / "Double.lean").write_text(DOUBLE, encoding="utf-8")
    (target_dir / "defs" / "Other.lean").write_text(OTHER, encoding="utf-8")
    scaffold.write(
        target_dir / "nodes",
        scaffold.Proposal(
            node_id=NODE,
            target_id=TARGET,
            statement=STATEMENT,
            witness="theorem witness : ∃ n : Nat, True := ⟨0, trivial⟩\n",
            author="curator",
            date="2026-10-29T00:00:00Z",
        ),
    )
    return ctx


def submit(tmp_path: Path, tc: LocalToolchain, files: dict[str, str]) -> tuple[RunContext, Any]:
    """The skeleton on ``doubling`` and ``files`` (name under the node -> text) as a diff."""
    ctx = context(tmp_path, tc)
    node = layout.graph_nodes_dir(ctx.graph_root, TARGET) / NODE
    st = layout.parse_statement((node / "Statement.lean").read_text(encoding="utf-8"))
    assert isinstance(st, layout.Statement)
    prefix = f"targets/{TARGET}/nodes/{NODE}/"
    (node / SKELETON).write_text(st.prefix + BODY, encoding="utf-8")
    ctx.changes = [Change("A", prefix + SKELETON)]
    for name, text in files.items():
        (node / name).write_text(text, encoding="utf-8")
        ctx.changes.append(Change("A", prefix + name))
    return ctx, pipeline.run_submission(ctx)


def witnesses(reported: dict[str, dict[str, Any]]) -> dict[str, str]:
    """Witness files of the types the precheck printed. Both holes ask for ``∃ (n : Nat), True``:
    a ``have … := sorry`` before ``second`` reaches it as a ``let`` the closed type drops, so
    ``second`` inherits no hypothesis from ``first`` here (measured at 4.33.1; F11-Q22 applies
    to a hole obtained from an earlier one, which this skeleton has none of)."""
    bodies = {"first": "⟨0, trivial⟩", "second": "⟨0, trivial⟩"}
    out: dict[str, str] = {}
    for n, name in enumerate(("first", "second"), 1):
        wanted = reported[name]["expected_witness"]
        assert wanted == "∃ (n : Nat), True", (name, reported[name])
        out[f"{STEM}.{n}{carried.SUFFIX}"] = (
            f"-- hole: {name}\nimport Defs.Double\n\ntheorem witness : {wanted} := {bodies[name]}\n"
        )
    return out


@pytest.fixture(scope="module")
def reported(
    tmp_path_factory: pytest.TempPathFactory, real_toolchain: LocalToolchain
) -> dict[str, Any]:
    _ctx, verdict = submit(tmp_path_factory.mktemp("precheck"), real_toolchain, {})
    assert verdict.verdict == "pass", verdict.as_dict()
    return {h["name"]: h for h in verdict.data["artifact"]["holes"]}


def test_a_carried_proof_with_a_helper_passes_as_its_node(
    tmp_path: Path, real_toolchain: LocalToolchain, reported: dict[str, Any]
) -> None:
    """AC5: the skeleton, witnesses for both holes and a proof of ``first`` with a helper pass
    every step; step 4's record names the proof; the composed file is the one built."""
    assert reported["first"]["closed_type"] == "∀ (n : Nat), Opn.double n = n + n", reported
    files = {**witnesses(reported), f"{STEM}.1{carried.PROOF_SUFFIX}": GOOD}
    _ctx, verdict = submit(tmp_path, real_toolchain, files)
    assert verdict.verdict == "pass", verdict.as_dict()
    step4 = next(s for s in verdict.steps if s.step == 4)
    assert step4.diagnostic is not None and step4.diagnostic.code == "hole-proofs"
    (entry,) = step4.diagnostic.details["proofs"]
    assert entry["hole"] == "first" and entry["node"] == CHILD
    (run,) = verdict.data[hole_proofs.RUNS_KEY]
    composed = (run.ctx.node.path / "Proof.lean").read_text(encoding="utf-8")
    assert HELPER in composed and "-- proof:" not in composed
    assert composed.startswith("import Defs.Double\n")
    assert [(r.step, r.result) for r in run.records] == [(n, "pass") for n in (1, 2, 4, 5, 6, 7, 8)]
    assert run.ctx.data["axioms"] == []  # the kernel's word on the composed proof
    assert verdict.data[hole_proofs.DATA_KEY] == [entry]


@pytest.mark.parametrize(
    ("label", "body"),
    [
        ("the sibling hole's theorem", "by\n  intro n\n  exact doubling__h2 n rfl\n"),
        ("the parent's theorem", f"by\n  intro n\n  exact ({DECL} n).1\n"),
        ("a lemma the statement does not import", "by\n  intro n\n  exact Opn.double_def n\n"),
    ],
)
def test_a_carried_proof_cannot_reach_past_its_statement(
    tmp_path: Path,
    real_toolchain: LocalToolchain,
    reported: dict[str, Any],
    label: str,
    body: str,
) -> None:
    """AC5, Q4: each names a constant that exists in the target; none is in the hole's reach,
    so the composed proof does not elaborate and the partial is refused at step 4."""
    files = {
        **witnesses(reported),
        f"{STEM}.1{carried.PROOF_SUFFIX}": f"-- hole: first\n-- proof:\n{body}",
    }
    ctx, verdict = submit(tmp_path, real_toolchain, files)
    assert verdict.first_failing_step == 4, (label, verdict.as_dict())
    assert verdict.diagnostic is not None
    assert verdict.diagnostic.code == "elaboration-failed", (label, verdict.diagnostic.as_dict())
    assert verdict.diagnostic.details["hole"] == "first"
    assert verdict.diagnostic.details["module"] == layout.node_module(CHILD, "Proof")
    assert hole_proofs.DATA_KEY not in verdict.data
    # Nothing merged: the graph has no node for the hole.
    assert not (layout.graph_nodes_dir(ctx.graph_root, TARGET) / CHILD).exists()
