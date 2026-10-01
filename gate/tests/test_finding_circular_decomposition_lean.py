"""F08-T17: a circularity claim's exhibit, checked by the real ``opn-relation-type`` (lean tier).

The fast tier (``test_finding_circular_decomposition``) proves the wiring with a fake relation
program. This proves the pinned Lean agrees on the one question the claim rests on — is the
exhibit's single theorem exactly ``<hole's statement> → <ancestor's statement>`` (F08-T21: the
hole implies what it was cut from, so the route from the ancestor leads straight back to it) — on
the fixture graph, core Lean only: the hole ``and-reassoc`` and the root ``and-swap-reassoc``
above it, whose statement imports its own Context, which restates the hole's theorem with a
``sorry`` body. So the root's statement file brings the hole's name into the environment, and the
relation program must read the hole's declaration from there rather than elaborate its file
again (the F08-T15 path, now taken for the variant too). The cheapest dishonest exhibit is a
``sorry`` where the ancestor's proof would go.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from harness import copy_graph
from test_finding_circular_decomposition import EXHIBIT, file_claim

from opn_gate import config, exhibits, layout, modes, schemas
from opn_gate.paths import Change, Claim
from opn_gate.steps.base import RunContext
from opn_gate.toolchain import LocalToolchain, ResolvedToolchain

pytestmark = pytest.mark.lean

TARGET = "propositional"
ANCESTOR_PROP = "(∀ p q r : Prop, (p ∧ q) ∧ r → r ∧ (q ∧ p))"
HOLE_PROP = "(∀ p q r : Prop, (p ∧ q) ∧ r → p ∧ (q ∧ r))"
#: ``ancestor → hole``: what F08-T17 asked for and F08-T21 refuses — it shows the hole is no
#: *harder* than the ancestor, which every provable hole satisfies.
REVERSE = (
    f"theorem circular : {ANCESTOR_PROP} → {HOLE_PROP} :=\n  fun _ _ _ _ h => ⟨h.1.1, h.1.2, h.2⟩\n"
)
UNRELATED = "theorem circular : True := trivial\n"
#: The right type with the ancestor's proof left as ``sorry``: claimed, not proved.
BORROWED = (
    "import Nodes.«and-swap-reassoc».Context\n\n"
    f"theorem circular : {HOLE_PROP} → {ANCESTOR_PROP} :=\n"
    "  fun _ => sorry\n"
)


def run_with(tmp_path: Path, tc: LocalToolchain, exhibit: str) -> list[str]:
    root = copy_graph(tmp_path / "g")
    rel = file_claim(root, exhibit=exhibit)
    classification = modes.classify([Change("A", rel)])
    assert modes.check(root, classification) == []
    spec_path = layout.gate_spec_path(root, TARGET)
    ctx = RunContext(
        graph_root=root,
        claim=Claim(TARGET, classification.node_id or ""),
        spec=schemas.load_json(spec_path, "gate-spec/v1"),
        gate_spec_hash=schemas.content_hash(spec_path.read_bytes()),
        changes=None,
        workdir=tmp_path / "work",
        toolchain=tc,
        settings=config.load({}),
    )
    return [d.code for d in exhibits.run(ctx, modes.exhibits(root, classification))]


def test_hole_implies_ancestor_passes_and_nothing_else_does(
    tmp_path: Path, real_toolchain: LocalToolchain, pinned: ResolvedToolchain, lean_pkg: Path
) -> None:
    assert run_with(tmp_path / "good", real_toolchain, EXHIBIT) == []
    assert run_with(tmp_path / "reverse", real_toolchain, REVERSE) == ["circular-direction"]
    assert run_with(tmp_path / "unrelated", real_toolchain, UNRELATED) == ["circular-direction"]
    assert run_with(tmp_path / "borrowed", real_toolchain, BORROWED) == ["circular-sorry"]
