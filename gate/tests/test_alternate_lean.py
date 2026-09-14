"""F07-T10: an alternate proof against the real toolchain (R7; AC27). make verify-lean.

The fast tier proves step 2 hands the alternate to step 4; only the real elaborator proves step 4
builds and replays *that file* — so a sound alternate passes and an ill-typed one fails at step 4
while the node's own ``Proof.lean`` is sound (one lean-tier test per new Lean-facing seam).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from test_pregate_lean import NODE, git_graph, run_pregate

from opn_gate import schemas

pytestmark = pytest.mark.lean

NAME = "20260914T120000Z-bob-alternate.lean"
BODY = "  exact ⟨h.2, h.1⟩\n"


def write_alternate(graph: Path, body: str) -> Path:
    """The tutorial's proof with its last line replaced, filed as an untracked alternate: the
    diff ``pregate.sh`` sees is exactly one added ``attempts/*-alternate.lean``."""
    proof = (graph / NODE / "Proof.lean").read_text(encoding="utf-8")
    text = proof.replace(BODY, body)
    assert text != proof  # guard: the fixture's proof still ends with BODY
    path = graph / NODE / "attempts" / NAME
    path.write_text(text, encoding="utf-8")
    return path


def test_real_alternate_passes(tmp_path: Path) -> None:
    """AC27: steps 1-8 pass on a differently-worded sound alternate and the attestation names it;
    one that does not typecheck fails at step 4, which it could only do if step 4 built it."""
    graph = git_graph(tmp_path / "sound")
    path = write_alternate(graph, "  exact And.intro h.2 h.1\n")
    code, summary = run_pregate(graph, tmp_path / "sound" / "out")
    assert code == 0, summary
    assert [(s["step"], s["result"]) for s in summary["steps"]] == [
        (1, "pass"),
        (2, "pass"),
        (4, "pass"),
        (5, "pass"),
        (6, "pass"),
        (7, "pass"),
        (8, "pass"),
    ]
    doc = json.loads((tmp_path / "sound" / "out" / "attestation.json").read_text())
    assert schemas.violations(doc) == []
    assert doc["artifact_hash"] == schemas.content_hash(path.read_bytes())

    broken = git_graph(tmp_path / "broken")
    write_alternate(broken, "  exact And.intro h.1 h.2\n")  # p ∧ q where q ∧ p is owed
    code, summary = run_pregate(broken, tmp_path / "broken" / "out")
    assert code == 1, summary
    assert summary["first_failing_step"] == 4, summary
