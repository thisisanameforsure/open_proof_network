"""F08-T27 (3 of 3; F18-T7): the footprints of merges attested before ``attestation/v6``.

Step 8 reads which nodes a proof term rests on, and since v6 the attestation keeps it. A merge
attested earlier has no such record, and an attestation is never edited (D-34), so the reading is
made once more, by the same steps, and kept beside the products in
``targets/<id>/.footprint-cache.json`` (``graph.FOOTPRINT_CACHE``), keyed by artifact hash.

Only what step 8 needs is run: the toolchain (1), the paths (2, which reads the declared uses),
the build and replay (4, which stages every dependency and use) and step 8 itself. The axiom,
hazard and witness steps decide nothing about which constants a term uses. A proof is measured as
the tree reads now (dependencies through their revisions, as step 8 always reads them), and an
alternate is measured by putting its text where step 4 stages an alternate: the node's
``Proof.lean``. A run that does not pass step 8 writes nothing: a failure is reported, never
recorded as an empty footprint (C7).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from opn_gate import attestation, graph, layout, pipeline, schemas
from opn_gate.steps.base import RunContext, Step
from opn_gate.steps.deps import DepsStep
from opn_gate.steps.paths_step import PathsStep
from opn_gate.steps.replay import KernelReplayStep
from opn_gate.steps.toolchain_step import ToolchainStep

#: Builds the run for one proof: the tree to gate, the node, and a work directory of its own.
ContextFactory = Callable[[str, Path], RunContext]


def steps() -> list[Step]:
    """Steps 1, 2, 4 and 8: what a footprint depends on, and nothing it does not."""
    return [ToolchainStep(), PathsStep(), KernelReplayStep(), DepsStep()]


@dataclass(frozen=True)
class Outcome:
    node_id: str
    path: str
    artifact_hash: str
    nodes: tuple[str, ...] | None  # None: step 8 did not pass
    failure: str | None

    def as_dict(self) -> dict[str, object]:
        return {
            "node_id": self.node_id,
            "path": self.path,
            "artifact_hash": self.artifact_hash,
            "nodes": None if self.nodes is None else list(self.nodes),
            "failure": self.failure,
        }


def unmeasured(tree: Path, target_id: str) -> list[tuple[str, graph.ProofRecord]]:
    """Every merged proof of the target whose record says nothing of what it used."""
    tg = graph.load_target(tree, target_id)
    return [(n, p) for n in tg.order for p in tg.nodes[n].proofs if p.used is None]


def measure(tree: Path, target_id: str, make_context: ContextFactory, work: Path) -> list[Outcome]:
    """Measure each unmeasured proof of ``target_id`` in ``tree``. ``make_context(node, out)``
    returns the run for one proof over a tree of its own (the caller exports one per run, so an
    alternate's text never reaches another proof's run)."""
    out: list[Outcome] = []
    for index, (node_id, proof) in enumerate(unmeasured(tree, target_id)):
        ctx = make_context(node_id, work / f"{index:04d}")
        if proof.kind == "alternate":
            node_dir = layout.graph_nodes_dir(tree, target_id) / node_id
            text = (node_dir / proof.path).read_bytes()
            run_dir = layout.graph_nodes_dir(ctx.graph_root, target_id) / node_id
            (run_dir / "Proof.lean").write_bytes(text)
        verdict = pipeline.run_steps(ctx, steps=steps())
        found = attestation.footprint_of(verdict)
        failure = None
        if found is None:
            d = verdict.diagnostic
            failure = f"step {verdict.first_failing_step}: {d.code if d else 'no diagnostic'}"
        out.append(
            Outcome(
                node_id=node_id,
                path=proof.path,
                artifact_hash=proof.artifact_hash,
                nodes=None if found is None else tuple(found["nodes"]),
                failure=failure,
            )
        )
    return out


def merged_cache(existing: dict[str, tuple[str, ...]], outcomes: list[Outcome]) -> bytes:
    """The cache file with every measured outcome added; a failed one adds nothing."""
    entries = {k: list(v) for k, v in existing.items()}
    for o in outcomes:
        if o.nodes is not None:
            entries[o.artifact_hash] = sorted(o.nodes)
    return schemas.canonical_json(dict(sorted(entries.items())))
