"""F08-T15, lean tier: a variant that declares the root as a dependency can carry a relation proof.

Found by the end-to-end run after the re-pin to network bb667de (agent E, graph PR #126), and read
through the service's new ``gate_verdict``: ``relation-elaboration``, "root statement does not
elaborate: `Opn.infinitude_of_primes` has already been declared". Since F08-T13 a proposed
statement imports its own ``Context``; when the root is one of its declared deps that Context
restates the root's theorem, and ``opn-relation-type`` then elaborated the root's file on top of
it. The natural variant — one that *uses* the root and proves how it relates to it — was
unadmittable, and no fixture combined the two (``variant-resolves`` declares no deps).

The node is built by the gate's own scaffold, so this is the shape that lands.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import samples
import yaml
from harness import GRAPH, TARGET, copy_graph

from opn_gate import admit, config, layout, scaffold, schemas
from opn_gate.paths import Claim
from opn_gate.steps.base import RunContext
from opn_gate.toolchain import LocalToolchain, ResolvedToolchain

pytestmark = pytest.mark.lean

ROOT = "and-swap-reassoc"
NODE = "variant-uses-root"
STATEMENT = (
    "/-! A variant of the root, in iff form (D-30), that draws on the root itself. -/\n\n"
    "theorem OpnProp.and_swap_reassoc_iff_again :\n"
    "    ∀ p q r : Prop, ((p ∧ q) ∧ r) ↔ (r ∧ (q ∧ p)) := by\n  sorry\n"
)
WITNESS = "theorem witness : ∃ p q r : Prop, True := ⟨True, True, True, trivial⟩\n"
RELATION = (
    "theorem relation :\n"
    "    (∀ p q r : Prop, ((p ∧ q) ∧ r) ↔ (r ∧ (q ∧ p))) →\n"
    "    (∀ p q r : Prop, (p ∧ q) ∧ r → r ∧ (q ∧ p)) :=\n"
    "  fun h p q r x => (h p q r).mp x\n"
)


def with_own_context(text: str) -> str:
    """As the service writes it (``proposals.with_own_context``): the import leads the file."""
    return f"import {layout.node_module(NODE, 'Context')}\n\n{text}"


def admit_variant(tmp_path: Path, tc: LocalToolchain, label: str) -> admit.Admission:
    root = copy_graph(tmp_path / "g", GRAPH)
    nodes = layout.graph_nodes_dir(root, TARGET)
    scaffold.write(
        nodes,
        scaffold.Proposal(
            node_id=NODE,
            target_id=TARGET,
            statement=with_own_context(STATEMENT),
            witness=with_own_context(WITNESS),
            author="someone",
            deps=(ROOT,),
            origin="variant",
            relation=label,
            relation_proof=with_own_context(RELATION),
        ),
    )
    # The live shape: the target declares its root (F11-T7). A variant that depends on the root
    # gives the root a dependent, so inference alone no longer names it.
    status = root / "targets" / TARGET / "status"
    status.mkdir(exist_ok=True)
    (status / "2026-09-12-curator.yaml").write_text(
        yaml.safe_dump(samples.target_status(root=ROOT)), encoding="utf-8"
    )
    context = (nodes / NODE / "Context.lean").read_text(encoding="utf-8")
    assert "and_swap_reassoc" in context  # the root's theorem, restated: the clash's cause
    spec_path = layout.gate_spec_path(root, TARGET)
    spec = schemas.load_json(spec_path, "gate-spec/v1")
    ctx = RunContext(
        graph_root=root,
        claim=Claim(TARGET, NODE),
        spec=spec,
        gate_spec_hash=schemas.content_hash(spec_path.read_bytes()),
        changes=None,
        workdir=tmp_path / "work",
        toolchain=tc,
        settings=config.load({}),
    )
    return admit.run(ctx)


def test_a_variant_that_depends_on_the_root_is_admitted_with_its_relation(
    tmp_path: Path, real_toolchain: LocalToolchain, pinned: ResolvedToolchain, lean_pkg: Path
) -> None:
    admission = admit_variant(tmp_path, real_toolchain, "resolves")
    assert admission.admitted, admission.as_dict()
    assert admission.data["relation"]["expected"] == admission.data["relation"]["declared"]


def test_the_direction_is_still_the_claim_on_that_path(
    tmp_path: Path, real_toolchain: LocalToolchain, pinned: ResolvedToolchain, lean_pkg: Path
) -> None:
    """The root's declaration now comes from the imported environment rather than from its file;
    the same proof labelled ``partial`` claims the converse and must still be refused."""
    admission = admit_variant(tmp_path, real_toolchain, "partial")
    assert not admission.admitted
    assert admission.diagnostic is not None
    assert admission.diagnostic.code == "relation-direction", admission.as_dict()
