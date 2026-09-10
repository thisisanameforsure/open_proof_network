"""F08-T4: an exhibit against the real toolchain (R6, R7). make verify-lean (lean tier).

The fast tier proves the wiring with a fake elaborator; this proves an exhibit that imports the
node's Context really elaborates, and one that does not really fails, under the pinned Lean.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import samples
import yaml
from harness import GRAPH, TARGET, TUTORIAL, copy_graph

from opn_gate import config, exhibits, layout, modes, schemas
from opn_gate.paths import Change, Claim
from opn_gate.steps.base import RunContext
from opn_gate.toolchain import LocalToolchain, ResolvedToolchain

pytestmark = pytest.mark.lean

GOOD = "import Nodes.«tutorial-and-swap».Context\n\nexample (p q : Prop) (h : p ∧ q) : q := h.2\n"
BAD = "import Nodes.«tutorial-and-swap».Context\n\nexample (p q : Prop) (h : p ∧ q) : q := h.1\n"


def run_with(tmp_path: Path, tc: LocalToolchain, exhibit: str) -> list[str]:
    root = copy_graph(tmp_path / "g", GRAPH)
    path = f"targets/{TARGET}/nodes/{TUTORIAL}/revisions/20260910T000000-alice.yaml"
    record = samples.revision_request(evidence={"text": "see the exhibit", "exhibit": exhibit})
    (root / path).parent.mkdir(parents=True)
    (root / path).write_text(yaml.safe_dump(record, sort_keys=True), encoding="utf-8")
    classification = modes.classify([Change("A", path)])
    assert modes.check(root, classification) == []
    spec_path = layout.gate_spec_path(root, TARGET)
    ctx = RunContext(
        graph_root=root,
        claim=Claim(TARGET, TUTORIAL),
        spec=schemas.load_json(spec_path, "gate-spec/v1"),
        gate_spec_hash=schemas.content_hash(spec_path.read_bytes()),
        changes=None,
        workdir=tmp_path / "work",
        toolchain=tc,
        settings=config.load({}),
    )
    return [d.code for d in exhibits.run(ctx, modes.exhibits(root, classification))]


def test_exhibit_elaborates_against_the_node(
    tmp_path: Path, real_toolchain: LocalToolchain, pinned: ResolvedToolchain, lean_pkg: Path
) -> None:
    assert run_with(tmp_path / "good", real_toolchain, GOOD) == []
    assert run_with(tmp_path / "bad", real_toolchain, BAD) == ["exhibit-elaboration"]
