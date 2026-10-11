"""F08-T27, F18-T7: the footprint of a merged proof on the real toolchain. make verify-lean.

The fast tier proves ``footprints.measure`` hands step 8's reading to the cache; only the real
elaborator proves the reading is the proof term's. The fixture root declares two dependencies and
its proof uses both; an alternate that reaches the conclusion through ``and_reassoc`` alone must
be measured as using that one node, with its declared-but-unused sibling left out — the
erdos-1050 shape, decided by the kernel term rather than by a fake (one lean-tier test per new
Lean-facing seam).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from harness import TARGET, copy_graph
from test_footprint_backfill import Factory, v5_attest
from test_node_proofs import proof_hash, proved_interior
from test_products import ROOT_NODE, nodes_dir

from opn_gate import footprints, schemas
from opn_gate.toolchain import LocalToolchain

pytestmark = pytest.mark.lean

A, B = "tutorial-and-swap", "and-reassoc"
ALTERNATE = "20260930T120000Z-bob-alternate.lean"


def test_the_kernel_term_decides_what_a_proof_used(
    tmp_path: Path, real_toolchain: LocalToolchain, lean_pkg: Path
) -> None:
    root = copy_graph(tmp_path / "g", publish=True)
    proved_interior(root)
    v5_attest(root, ROOT_NODE, 3, proof_hash(root, ROOT_NODE))
    node = nodes_dir(root) / ROOT_NODE
    proof = (node / "Proof.lean").read_text(encoding="utf-8")
    body = "  exact ⟨h2.2.2, OpnProp.and_swap p q h.1⟩\n"
    assert body in proof  # guard: the fixture's proof still ends this way
    alternate = proof.replace(body, "  exact ⟨h2.2.2, h2.2.1, h2.1⟩\n")
    (node / "attempts").mkdir(exist_ok=True)
    (node / "attempts" / ALTERNATE).write_text(alternate, encoding="utf-8")
    v5_attest(root, ROOT_NODE, 4, schemas.content_hash(alternate.encode("utf-8")))

    tc = LocalToolchain(real_toolchain.elan, lean_pkg)
    outcomes = footprints.measure(root, TARGET, Factory(root, tc), tmp_path / "w")  # type: ignore[arg-type]
    assert [(o.path, o.nodes, o.failure) for o in outcomes] == [
        ("Proof.lean", tuple(sorted([A, B])), None),
        (f"attempts/{ALTERNATE}", (B,), None),
    ]
