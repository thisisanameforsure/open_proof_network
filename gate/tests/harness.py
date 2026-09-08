"""Test harness: a RunContext over a scratch copy of the propositional fixture graph."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from fakes import FakeToolchain

from opn_gate import config, layout, paths, schemas
from opn_gate.paths import Change, Claim
from opn_gate.steps.base import RunContext

FIXTURES = Path(__file__).resolve().parent / "fixtures"
GRAPH = FIXTURES / "graphs" / "propositional"
TARGET = "propositional"
TUTORIAL = "tutorial-and-swap"


def copy_graph(tmp_path: Path) -> Path:
    root = tmp_path / "graph"
    shutil.copytree(GRAPH, root)
    return root


def proof_only_changes(node_id: str = TUTORIAL) -> list[Change]:
    return [Change("A", f"targets/{TARGET}/nodes/{node_id}/Proof.lean")]


def make_context(
    tmp_path: Path,
    *,
    node_id: str = TUTORIAL,
    toolchain: Any | None = None,
    changes: list[Change] | None = None,
    spec_overrides: dict[str, Any] | None = None,
    settings: config.Settings | None = None,
) -> RunContext:
    root = copy_graph(tmp_path)
    spec_path = layout.gate_spec_path(root, TARGET)
    spec = schemas.load_json(spec_path, "gate-spec/v1")
    if spec_overrides:
        spec.update(spec_overrides)
        spec_path.write_bytes(schemas.canonical_json(spec))
    return RunContext(
        graph_root=root,
        claim=Claim(TARGET, node_id),
        spec=spec,
        gate_spec_hash=schemas.content_hash(spec_path.read_bytes()),
        changes=proof_only_changes(node_id) if changes is None else changes,
        workdir=tmp_path / "work",
        toolchain=toolchain if toolchain is not None else FakeToolchain(),
        settings=settings or config.load({}),
    )


def node_dir(ctx: RunContext) -> Path:
    return layout.graph_nodes_dir(ctx.graph_root, ctx.claim.target_id) / ctx.claim.node_id


def changes_against_fixture(ctx: RunContext) -> list[Change]:
    """Diff the scratch copy against the pristine fixture, as a submission would be diffed."""
    return paths.changes_from_trees(GRAPH, ctx.graph_root)
