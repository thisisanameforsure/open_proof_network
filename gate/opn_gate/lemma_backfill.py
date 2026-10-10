"""F08-T41 (D-12 v3.36): the lemma edges of merges made before the rule, written once more.

A hole of a merged partial that restated a node under another branch of the target is a lemma of
the parent (``META.yaml``'s ``lemmas``, F07-T77). Before v3.36 the post-merge writer recognised
the restatement — step 4's ``defeq_sibling`` — and recorded it in its log and nowhere else, so a
live parent (``erdos-1094--h3``, graph #479) has a merged assembly it cannot use. An attestation
is never edited (D-34) and the placement reached no record, so the reading is made once more: for
every merged partial of every node of the target, the same steps that judged it (1, 2 and 4, whose
last word is the artifact extraction) are run again over the tree as it stands, and every
restatement of a node that is not the parent's own hole child becomes the edge the writer would
record today — ``postmerge.add_lemmas`` and the regenerated ``Context.lean``, nothing else.

Idempotent: an edge already on the record is reported ``unchanged`` and nothing is rewritten; a
partial the steps no longer pass (a parent since proved, an assembly that no longer builds) is
reported ``failed`` and writes nothing (C7). The extractor needs the toolchain, so a Mathlib
target runs this in the step-3 sandbox (``opn-gate lemmas-backfill``); the fast tier drives it
over the fixture with the fake.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from opn_gate import graph, layout, pipeline, postmerge
from opn_gate.paths import Change
from opn_gate.steps.artifact import Hole
from opn_gate.steps.base import RunContext, Step
from opn_gate.steps.paths_step import PathsStep
from opn_gate.steps.replay import KernelReplayStep
from opn_gate.steps.toolchain_step import ToolchainStep

#: Builds the run for one partial: the node, and a work directory of its own. The caller exports
#: one tree per run (as the footprint backfill does); this module sets the run's ``changes`` to
#: the partial's file, so step 2 takes it as the submission it was.
ContextFactory = Callable[[str, Path], RunContext]


def steps() -> list[Step]:
    """Steps 1, 2 and 4: what the extraction depends on, and nothing it does not. Step 4's last
    word is the artifact judgment, which is where the holes and their restatements come from."""
    return [ToolchainStep(), PathsStep(), KernelReplayStep()]


@dataclass(frozen=True)
class Edge:
    node: str
    hole: str
    lemma: str

    def as_dict(self) -> dict[str, str]:
        return {"node": self.node, "hole": self.hole, "lemma": self.lemma}


@dataclass(frozen=True)
class Failure:
    node: str
    partial: str
    failure: str

    def as_dict(self) -> dict[str, str]:
        return {"node": self.node, "partial": self.partial, "failure": self.failure}


@dataclass
class Report:
    written: list[Edge] = field(default_factory=list)
    unchanged: list[Edge] = field(default_factory=list)
    failed: list[Failure] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "written": [e.as_dict() for e in self.written],
            "unchanged": [e.as_dict() for e in self.unchanged],
            "failed": [f.as_dict() for f in self.failed],
        }


def candidates(graph_root: Path, target_id: str) -> list[tuple[str, graph.PartialRecord]]:
    """Every merged partial of every node of the target, in the graph's order."""
    tg = graph.load_target(graph_root, target_id)
    return [(n, p) for n in tg.order for p in tg.nodes[n].partials]


def recorded_lemma_nodes(node_dir: Path) -> set[str]:
    """The nodes ``META.yaml``'s ``lemmas`` already name, as written and as each is now (a
    revision read through, so an edge to a since-revised node is not written twice)."""
    nodes_dir = node_dir.parent
    recorded = postmerge.add_lemmas(node_dir, [])  # a read: nothing new, nothing written
    out = {entry["node"] for entry in recorded}
    out.update(lm.node for lm in graph.effective_lemmas(nodes_dir, recorded))
    return out


def backfill(graph_root: Path, target_id: str, make_context: ContextFactory, work: Path) -> Report:
    """Re-extract each merged partial of ``target_id`` and write the lemma edges the record
    lacks into ``graph_root``'s nodes. ``make_context(node, out)`` returns the run for one
    partial over a tree of its own; its ``changes`` are set here to the partial's file."""
    report = Report()
    nodes_dir = layout.graph_nodes_dir(graph_root, target_id)
    for index, (node_id, partial) in enumerate(candidates(graph_root, target_id)):
        ctx = make_context(node_id, work / f"{index:04d}")
        ctx.changes = [Change("A", f"targets/{target_id}/nodes/{node_id}/{partial.path}")]
        verdict = pipeline.run_steps(ctx, steps=steps())
        artifact = verdict.data.get("artifact")
        if not verdict.ok or not isinstance(artifact, dict):
            d = verdict.diagnostic
            report.failed.append(
                Failure(
                    node_id,
                    partial.path,
                    f"step {verdict.first_failing_step}: {d.code if d else 'no diagnostic'}",
                )
            )
            continue
        node_dir = nodes_dir / node_id
        known = recorded_lemma_nodes(node_dir)
        for hole in (Hole.of(h) for h in artifact.get("holes") or [] if isinstance(h, dict)):
            if not hole.defeq_sibling:
                continue
            try:
                sibling = postmerge.reused_node(nodes_dir, node_id, hole)
            except postmerge.GraphWriteError as exc:
                report.failed.append(Failure(node_id, partial.path, str(exc)))
                continue
            if sibling is None or graph.is_hole_child(nodes_dir, node_id, sibling):
                continue  # the parent's own hole: an edge already on the record (R22)
            edge = Edge(node_id, hole.name, sibling)
            if sibling in known:
                report.unchanged.append(edge)
                continue
            postmerge.add_lemmas(node_dir, [(hole.name, sibling)])
            postmerge.regenerate_context(node_dir, nodes_dir)
            known.add(sibling)
            report.written.append(edge)
    return report
