"""F08-T5: consolidation's definitional-equality probe against the real toolchain (R10).

make verify-lean (lean tier). The fast tier proves the probe's shape with a fake elaborator;
this proves Lean accepts it for two statements that differ only in layout and rejects it for two
that differ in meaning.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from harness import GRAPH, TARGET, copy_graph

from opn_gate import config, curator, layout, schemas
from opn_gate.paths import Claim
from opn_gate.steps.base import RunContext
from opn_gate.toolchain import LocalToolchain, ResolvedToolchain

pytestmark = pytest.mark.lean

INTERIOR = "and-reassoc"
ROOT = "and-swap-reassoc"


def clone_node(root: Path, source: str, new_id: str, *, statement: str) -> None:
    nodes = layout.graph_nodes_dir(root, TARGET)
    dest = nodes / new_id
    dest.mkdir()
    for name in ("Witness.lean", "Context.lean"):
        (dest / name).write_text(
            (nodes / source / name).read_text().replace(f"«{source}»", f"«{new_id}»")
        )
    (dest / "Statement.lean").write_text(statement.replace(f"«{source}»", f"«{new_id}»"))
    meta = yaml.safe_load((nodes / source / "META.yaml").read_text())
    meta["id"] = new_id
    parsed = layout.parse_statement((dest / "Statement.lean").read_text())
    assert isinstance(parsed, layout.Statement)
    meta["statement-hash"] = parsed.statement_hash
    (dest / "META.yaml").write_text(yaml.safe_dump(meta, sort_keys=False))
    for d in layout.REQUIRED_DIRS:
        (dest / d).mkdir()
        (dest / d / layout.KEEP_FILE).write_text("")


def defeq(root: Path, tc: LocalToolchain, workdir: Path) -> curator.Defeq:
    spec_path = layout.gate_spec_path(root, TARGET)
    ctx = RunContext(
        graph_root=root,
        claim=Claim(TARGET, INTERIOR),
        spec=schemas.load_json(spec_path, "gate-spec/v1"),
        gate_spec_hash=schemas.content_hash(spec_path.read_bytes()),
        changes=None,
        workdir=workdir,
        toolchain=tc,
        settings=config.load({}),
    )
    return lambda kept, dropped: curator.statements_defeq(ctx, kept, dropped)


def test_consolidate_defeq_with_lean(
    tmp_path: Path, real_toolchain: LocalToolchain, pinned: ResolvedToolchain, lean_pkg: Path
) -> None:
    root = copy_graph(tmp_path, GRAPH)
    nodes = layout.graph_nodes_dir(root, TARGET)
    original = (nodes / INTERIOR / "Statement.lean").read_text()
    # The same theorem with a comment added: different bytes, the same type — a duplicate.
    relaid = original.replace("theorem ", "-- laid out again\ntheorem ", 1)
    assert relaid != original
    clone_node(root, INTERIOR, "and-reassoc-again", statement=relaid)
    check = defeq(root, real_toolchain, tmp_path / "work-same")
    record = curator.consolidate(
        root,
        TARGET,
        INTERIOR,
        "and-reassoc-again",
        author="c",
        date="2026-09-10T00:00:00Z",
        defeq=check,
    )
    assert "definitionally equal" in yaml.safe_load(record.read_text())["cause"]

    # A different theorem is not a duplicate, whatever the curator says.
    with pytest.raises(curator.CuratorError, match="definitionally equal types"):
        curator.consolidate(
            root,
            TARGET,
            ROOT,
            INTERIOR,
            author="c",
            date="2026-09-10T00:00:01Z",
            defeq=defeq(root, real_toolchain, tmp_path / "work-diff"),
        )
