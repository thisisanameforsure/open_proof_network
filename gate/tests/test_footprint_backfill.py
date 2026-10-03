"""F08-T27 (3 of 3), F18-T7: ``opn-gate footprints`` measures merges attested before v6.

The same steps that measure a new merge (1, 2, 4 and 8) measure an old one, so the cache says what
the attestation would have said. Fast tier over the fake toolchain; the lean tier runs it on the
real toolchain (``test_footprint_backfill_lean.py``).
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from fakes import LIBRARY_CONSTANTS, FakeToolchain, used_constants_result
from harness import TARGET, copy_graph
from test_node_proofs import graph_row, proof_hash, proved_interior
from test_products import ROOT_NODE, attest, nodes_dir

from opn_gate import config, footprints, graph, layout, schemas
from opn_gate.paths import Claim
from opn_gate.steps.base import RunContext

A, B = "tutorial-and-swap", "and-reassoc"
A_MOD, B_MOD = f"Nodes.«{A}».Proof", f"Nodes.«{B}».Proof"


def v5_attest(root: Path, node_id: str, n: int, artifact_hash: str) -> None:
    """An attestation as a gate before F08-T27 wrote it: v5, no footprint."""
    attest(root, node_id, n=n, artifact_hash=artifact_hash, schema="attestation/v5")
    path = root / "attestations" / f"{n:06d}.json"
    doc = json.loads(path.read_text())
    del doc["footprint"]
    path.write_bytes(schemas.canonical_json(doc))


class Factory:
    """One exported tree per run, as the CLI exports one per proof; remembers each run."""

    def __init__(self, tree: Path, toolchain: FakeToolchain) -> None:
        self.tree, self.toolchain = tree, toolchain
        self.runs: list[RunContext] = []

    def __call__(self, node_id: str, out: Path) -> RunContext:
        run_tree = out / "tree"
        shutil.copytree(self.tree, run_tree)
        spec_path = layout.gate_spec_path(run_tree, TARGET)
        ctx = RunContext(
            graph_root=run_tree,
            claim=Claim(TARGET, node_id),
            spec=schemas.load_json(spec_path, "gate-spec/v1"),
            gate_spec_hash=schemas.content_hash(spec_path.read_bytes()),
            changes=None,
            workdir=out / "work",
            toolchain=self.toolchain,
            settings=config.load({}),
        )
        self.runs.append(ctx)
        return ctx


def measured_proof(root: Path) -> None:
    attest(
        root, ROOT_NODE, n=3, artifact_hash=proof_hash(root, ROOT_NODE), footprint={"nodes": [A]}
    )


def uses_a() -> FakeToolchain:
    return FakeToolchain(
        constants=used_constants_result([*LIBRARY_CONSTANTS, ("OpnProp.and_swap", A_MOD)])
    )


def test_an_old_merge_is_measured_and_the_cache_completes_the_product(tmp_path: Path) -> None:
    root = copy_graph(tmp_path / "g", publish=True)
    proved_interior(root)
    v5_attest(root, ROOT_NODE, 3, proof_hash(root, ROOT_NODE))
    assert graph_row(root, ROOT_NODE)["proofs"][0]["used"] is None  # not measured yet
    outcomes = footprints.measure(root, TARGET, Factory(root, uses_a()), tmp_path / "w")
    assert [(o.node_id, o.path, o.nodes, o.failure) for o in outcomes] == [
        (ROOT_NODE, "Proof.lean", (A,), None)
    ]
    cache = root / "targets" / TARGET / graph.FOOTPRINT_CACHE
    cache.write_bytes(footprints.merged_cache({}, outcomes))
    assert graph_row(root, ROOT_NODE)["proofs"][0]["used"] == [A]
    # Measured once: a second pass finds nothing left to measure.
    assert footprints.unmeasured(root, TARGET) == []


def test_an_alternate_is_measured_on_its_own_text(tmp_path: Path) -> None:
    root = copy_graph(tmp_path / "g", publish=True)
    proved_interior(root)
    attest(
        root, ROOT_NODE, n=3, artifact_hash=proof_hash(root, ROOT_NODE), footprint={"nodes": [A]}
    )
    alt = nodes_dir(root) / ROOT_NODE / "attempts" / "20260930T120000Z-bob-alternate.lean"
    alt.parent.mkdir(exist_ok=True)
    alt.write_text((nodes_dir(root) / ROOT_NODE / "Proof.lean").read_text() + "\n-- again\n")
    alt_hash = schemas.content_hash(alt.read_bytes())
    v5_attest(root, ROOT_NODE, 4, alt_hash)
    factory = Factory(root, uses_a())
    [outcome] = footprints.measure(root, TARGET, factory, tmp_path / "w")
    assert (outcome.path, outcome.artifact_hash, outcome.nodes) == (
        alt.relative_to(alt.parent.parent).as_posix(),
        alt_hash,
        (A,),
    )
    [run] = factory.runs
    staged = nodes_dir(run.graph_root) / ROOT_NODE / "Proof.lean"
    assert staged.read_bytes() == alt.read_bytes()  # the alternate, where step 4 stages one
    assert (nodes_dir(root) / ROOT_NODE / "Proof.lean").read_bytes() != alt.read_bytes()


def test_a_run_that_fails_step_eight_records_nothing(tmp_path: Path) -> None:
    root = copy_graph(tmp_path / "g", publish=True)
    proved_interior(root)
    v5_attest(root, ROOT_NODE, 3, proof_hash(root, ROOT_NODE))
    mystery = FakeToolchain(constants=used_constants_result([("mystery", "Somewhere.Else")]))
    [outcome] = footprints.measure(root, TARGET, Factory(root, mystery), tmp_path / "w")
    assert outcome.nodes is None and outcome.failure == "step 8: undeclared-dependency"
    assert json.loads(footprints.merged_cache({}, [outcome])) == {}


def test_a_measured_merge_is_not_measured_again(tmp_path: Path) -> None:
    root = copy_graph(tmp_path / "g", publish=True)
    proved_interior(root)
    attest(
        root, ROOT_NODE, n=3, artifact_hash=proof_hash(root, ROOT_NODE), footprint={"nodes": [A]}
    )
    factory = Factory(root, uses_a())
    assert footprints.measure(root, TARGET, factory, tmp_path / "w") == []
    assert factory.runs == []


def test_the_cache_keeps_what_it_had_and_sorts(tmp_path: Path) -> None:
    out = footprints.Outcome("n", "Proof.lean", "b" * 64, (B, A), None)
    merged = json.loads(footprints.merged_cache({"a" * 64: (A,)}, [out]))
    assert merged == {"a" * 64: [A], "b" * 64: sorted([A, B])}
