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
ADVERSARIAL = FIXTURES / "graphs" / "adversarial"
TARGET = "propositional"
TUTORIAL = "tutorial-and-swap"


def copy_graph(tmp_path: Path, graph: Path = GRAPH) -> Path:
    root = tmp_path / "graph"
    shutil.copytree(graph, root)
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
    graph: Path = GRAPH,
    target: str = TARGET,
) -> RunContext:
    root = copy_graph(tmp_path, graph)
    spec_path = layout.gate_spec_path(root, target)
    spec = schemas.load_json(spec_path, "gate-spec/v1")
    if spec_overrides:
        spec.update(spec_overrides)
        spec_path.write_bytes(schemas.canonical_json(spec))
    return RunContext(
        graph_root=root,
        claim=Claim(target, node_id),
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


#: F11: a curated target, taken in through ``intake.new`` with admission faked out. The fast tier
#: has no Lean (conventions §2), and every refusal intake has is about the *record* — so the seam
#: is where the toolchain stops and the tests keep going.
def always_admits(path: Path, subject: str) -> Any:
    from opn_gate import intake  # noqa: PLC0415 — only the F11 helpers need it

    return intake.SubjectCheck(subject, True, "admission faked in the fast tier")


def take_in(
    graph_root: Path,
    target_id: str = "euclid-primes",
    *,
    source_node: str = "and-reassoc",
    root_dir: Path | None = None,
    defs: dict[str, str] | None = None,
    checker: Any = None,
    author: str = "curator",
    date: str = "2026-09-11T00:00:00Z",
    **record_overrides: Any,
) -> Any:
    """Take a target in, reusing one of the fixture's nodes as its root."""
    import samples  # noqa: PLC0415

    from opn_gate import intake  # noqa: PLC0415

    node_dir = root_dir or graph_root / "targets" / TARGET / "nodes" / source_node
    defs_dir: Path | None = None
    if defs is not None:
        defs_dir = graph_root.parent / f"{target_id}-defs"
        defs_dir.mkdir(parents=True, exist_ok=True)
        for name, text in defs.items():
            (defs_dir / name).write_text(text, encoding="utf-8")
    spec = schemas.load_json(layout.gate_spec_path(graph_root, TARGET), "gate-spec/v1")
    doc = samples.target_record(id=target_id, **record_overrides)
    return intake.new(
        graph_root,
        target_id,
        doc=doc,
        root_dir=node_dir,
        defs_dir=defs_dir,
        spec_template=spec,
        checker=checker if checker is not None else always_admits,
        author=author,
        date=date,
    )
