"""F11-T13: a definition added after intake, against the real toolchain. make verify-lean.

The fast tier proves the route and its wiring with a fake elaborator; this proves the sandbox
step's build really compiles a new ``defs/`` file on the merged tree, really refuses one that
does not elaborate, and leaves a module a later file can import (F11-AC35).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from harness import GRAPH, TARGET, copy_graph

from opn_gate import cli, config, layout, modes, schemas
from opn_gate.paths import Change, Claim
from opn_gate.steps.base import RunContext
from opn_gate.toolchain import LocalToolchain, ResolvedToolchain

pytestmark = pytest.mark.lean

CURATOR = "thisisanameforsure"
GOOD = "def Opn.helper : Nat := 2\n"
BAD = 'def Opn.helper : Nat := "two"\n'
USER = "import Defs.Helper\n\nexample : Opn.helper = 2 := rfl\n"


def added(tmp_path: Path, tc: LocalToolchain, text: str) -> tuple[RunContext, list[str]]:
    root = copy_graph(tmp_path / "g", GRAPH)
    rel = f"targets/{TARGET}/defs/Helper.lean"
    (root / rel).write_text(text, encoding="utf-8")
    curators = modes.Curators(identities=((CURATOR, CURATOR),))
    classification = modes.classify([Change("A", rel)], author=CURATOR, curators=curators)
    assert classification.mode == "curator" and modes.check(root, classification) == []
    spec_path = layout.gate_spec_path(root, TARGET)
    ctx = RunContext(
        graph_root=root,
        claim=Claim(TARGET, ""),
        spec=schemas.load_json(spec_path, "gate-spec/v1"),
        gate_spec_hash=schemas.content_hash(spec_path.read_bytes()),
        changes=None,
        workdir=tmp_path / "work",
        toolchain=tc,
        settings=config.load({}),
    )
    return ctx, [d.code for d in cli._elaborate_definitions(ctx, spec_path.parent)]


def test_a_new_definition_builds_and_a_later_file_imports_it(
    tmp_path: Path, real_toolchain: LocalToolchain, pinned: ResolvedToolchain, lean_pkg: Path
) -> None:
    ctx, problems = added(tmp_path / "good", real_toolchain, GOOD)
    assert problems == []
    src = ctx.workdir / "src"
    probe = src / "Probe.lean"
    probe.write_text(USER, encoding="utf-8")
    elab = real_toolchain.elaborate(
        ctx.data["toolchain"], probe, "Probe", ctx.build_dir, root=src, timeout_s=ctx.wallclock_s
    )
    assert elab.ok, elab.messages


def test_a_new_definition_that_does_not_elaborate_is_refused(
    tmp_path: Path, real_toolchain: LocalToolchain, pinned: ResolvedToolchain, lean_pkg: Path
) -> None:
    _ctx, problems = added(tmp_path / "bad", real_toolchain, BAD)
    assert problems == ["defs-elaboration"]
