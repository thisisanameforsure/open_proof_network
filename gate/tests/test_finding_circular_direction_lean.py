"""Finding: a circularity claim's exhibit proved the wrong implication (lean tier).

Found 2026-09-29 by tester 69-C (B3; bugs.md item 5): F08-T17 checked an exhibit of type
``ancestor → hole``, and D-16 read that as "the hole is no easier than what it was meant to
reduce". It says the opposite — the hole is no *harder* than the ancestor — so any provable hole
(the tester's probe: ``intro _`` then the hole's merged proof) and any hole whose hypothesis
contradicts the ancestor (``intro hroot hq; exact absurd …``) met the check, and one merged claim
could take a genuinely easier hole off the frontier. Nothing was filed, but nothing would have
refused it.

The owner's rule: what qualifies as circular is literal — you start at the premise and you end at
it. The exhibit therefore proves ``hole → ancestor``: any proof of the hole is a proof of the
ancestor, so from the ancestor the decomposition leads to the hole and the hole leads straight
back. A hole that is the ancestor restated passes by ``exact``; a hole that is strictly easier
cannot pass unless the ancestor itself is proved.

Two closed tautologies cannot be strictly ordered (each implies the other), so the fixture states
its problems over two ``opaque`` propositions the environment knows nothing about — the honest
model of an open problem — in the target's ``defs/``: the ancestor ``strong : S ∧ T`` with the
holes ``weak : S`` (strictly weaker), ``vacuous : ¬S → T`` (provable from the ancestor by
contradicting it) and ``same : S ∧ T`` (the ancestor restated), the ancestor's Context restating
each hole as a declared dependency's Context does. Core Lean only, run by the real
``opn-relation-type``.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from harness import TARGET, copy_graph
from test_finding_circular_decomposition import file_claim

from opn_gate import config, exhibits, layout, modes, schemas
from opn_gate.diagnostic import Diagnostic
from opn_gate.paths import Change, Claim
from opn_gate.steps.base import RunContext
from opn_gate.toolchain import LocalToolchain, ResolvedToolchain

pytestmark = pytest.mark.lean

ANCESTOR = "strong"
WEAK = "weak"
VACUOUS = "vacuous"
SAME = "same"
HOLES = {
    WEAK: ("OpnProp.weak", "OpnProp.S"),
    VACUOUS: ("OpnProp.vacuous", "¬ OpnProp.S → OpnProp.T"),
    SAME: ("OpnProp.same", "OpnProp.S ∧ OpnProp.T"),
}
ANCESTOR_PROP = "OpnProp.S ∧ OpnProp.T"
#: What ``opn-relation-type`` prints for ``(expected, declared)`` on each refused exhibit — Lean's
#: own rendering (``¬OpnProp.S``, an arrow antecedent in parentheses), pinned so the refusal names
#: what the exhibit proved in the words the contributor will read.
PRINTED = {
    WEAK: (f"OpnProp.S → {ANCESTOR_PROP}", f"{ANCESTOR_PROP} → OpnProp.S"),
    VACUOUS: (
        f"(¬OpnProp.S → OpnProp.T) → {ANCESTOR_PROP}",
        f"{ANCESTOR_PROP} → ¬OpnProp.S → OpnProp.T",
    ),
}
DEFS = (
    "/-! Two propositions the environment knows nothing about: the fixture's open problems. -/\n\n"
    "opaque OpnProp.S : Prop\n"
    "opaque OpnProp.T : Prop\n"
)
IMPORT = "import Defs.Opaque\n\n"

#: The tester's probe: the hole proved from the ancestor by projection — ``ancestor → hole``.
EASIER = IMPORT + f"theorem circular : {ANCESTOR_PROP} → OpnProp.S :=\n  fun h => h.1\n"
#: The vacuous shape: the hole's hypothesis contradicts the ancestor, so anything follows.
ABSURD = IMPORT + (
    f"theorem circular : {ANCESTOR_PROP} → ¬ OpnProp.S → OpnProp.T :=\n"
    "  fun h hn => absurd h.1 hn\n"
)
#: The hole is the ancestor restated: ``hole → ancestor`` by ``exact``.
RESTATED = IMPORT + (
    f"theorem circular : {ANCESTOR_PROP} → {ANCESTOR_PROP} := by\n  intro h\n  exact h\n"
)
#: ``weak → strong`` cannot be written without proving ``T``, which is the ancestor's own work.
UNPROVED = IMPORT + f"theorem circular : OpnProp.S → {ANCESTOR_PROP} :=\n  fun h => ⟨h, sorry⟩\n"


def node(nodes: Path, node_id: str, decl: str, prop: str, *, context: str, deps: list[str]) -> None:
    directory = nodes / node_id
    directory.mkdir()
    for name in layout.REQUIRED_DIRS:
        (directory / name).mkdir()
    statement = f"{IMPORT}theorem {decl} : {prop} := by\n  sorry\n"
    if deps:
        statement = f"import Nodes.«{node_id}».Context\n\ntheorem {decl} : {prop} := by\n  sorry\n"
    (directory / "Statement.lean").write_text(statement, encoding="utf-8")
    (directory / "Context.lean").write_text(context, encoding="utf-8")
    (directory / "Witness.lean").write_text("theorem witness : True := trivial\n", encoding="utf-8")
    meta = yaml.safe_load((nodes / "and-reassoc" / "META.yaml").read_text(encoding="utf-8"))
    meta.update(
        {
            "id": node_id,
            "deps": deps,
            "status": "blocked" if deps else "ready",
            "statement-hash": schemas.content_hash(statement.encode("utf-8")),
        }
    )
    (directory / "META.yaml").write_text(yaml.safe_dump(meta, sort_keys=False), encoding="utf-8")


def open_problem(tmp_path: Path) -> Path:
    """The fixture graph plus the opaque target: ``strong`` decomposed into three holes."""
    root = copy_graph(tmp_path)
    target = root / "targets" / TARGET
    (target / "defs" / "Opaque.lean").write_text(DEFS, encoding="utf-8")
    nodes = target / "nodes"
    for node_id, (decl, prop) in HOLES.items():
        node(nodes, node_id, decl, prop, context="/-! Declared dependencies: none. -/\n", deps=[])
    restated = "".join(
        f"theorem {decl} : {prop} := by\n  sorry\n\n" for decl, prop in HOLES.values()
    )
    node(
        nodes,
        ANCESTOR,
        "OpnProp.strong",
        ANCESTOR_PROP,
        context=f"{IMPORT}/-! Declared dependencies (D-4 step 8): the holes. -/\n\n{restated}",
        deps=list(HOLES),
    )
    return root


def run_with(tmp_path: Path, tc: LocalToolchain, hole: str, exhibit: str) -> list[Diagnostic]:
    root = open_problem(tmp_path / "g")
    rel = f"targets/{TARGET}/nodes/{hole}/defects/20260929T192222Z-tester.yaml"
    file_claim(root, rel, stmt_ref=hole, ancestor=ANCESTOR, exhibit=exhibit)
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
    return exhibits.run(ctx, modes.exhibits(root, classification))


@pytest.mark.parametrize(
    ("hole", "exhibit"), [(WEAK, EASIER), (VACUOUS, ABSURD)], ids=["easier", "absurd"]
)
def test_an_exhibit_of_ancestor_implies_hole_is_refused(
    tmp_path: Path,
    *,
    real_toolchain: LocalToolchain,
    pinned: ResolvedToolchain,
    lean_pkg: Path,
    hole: str,
    exhibit: str,
) -> None:
    """The defect: the shipped gate accepted both of these as circular."""
    found = run_with(tmp_path, real_toolchain, hole, exhibit)
    assert [d.code for d in found] == ["circular-direction"], found
    details = found[0].details or {}
    expected, declared = PRINTED[hole]
    assert details["expected"] == expected, "the hole implies the ancestor"
    assert details["declared"] == declared, "what the exhibit proved"
    assert f"({hole} → {ANCESTOR}" in found[0].message
    assert declared in found[0].message, "the refusal names what it proved"


def test_a_hole_that_is_the_ancestor_restated_passes_by_exact(
    tmp_path: Path, real_toolchain: LocalToolchain, pinned: ResolvedToolchain, lean_pkg: Path
) -> None:
    assert run_with(tmp_path, real_toolchain, SAME, RESTATED) == []


def test_an_easier_hole_cannot_be_shown_circular_without_proving_the_ancestor(
    tmp_path: Path, real_toolchain: LocalToolchain, pinned: ResolvedToolchain, lean_pkg: Path
) -> None:
    """``weak → strong`` needs ``T``: a proof of the ancestor's other half, which is the open
    problem. The only way to write the exhibit is ``sorry``, and that is refused by name."""
    found = run_with(tmp_path, real_toolchain, WEAK, UNPROVED)
    assert [d.code for d in found] == ["circular-sorry"], found
