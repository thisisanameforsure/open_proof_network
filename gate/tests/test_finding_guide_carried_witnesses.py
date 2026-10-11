"""F07-T52, T53 (R23, AC47, AC48): the guide says how a skeleton carries its holes' witnesses.

An agent reads the guide and not the code (log, 2026-09-11: docs are tests), and the 2026-10-01
testers paid a second queue pass per hole for want of this route. Where a sentence states a
suffix, a marker or a code the gate defines, the test reads the gate's value, so the two cannot
drift.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from opn_gate import carried

ROOT = Path(__file__).resolve().parents[2]
GUIDE = (ROOT / "gate" / "agents" / "AGENTS.md").read_text(encoding="utf-8")
FLAT = re.sub(r"\s+", " ", GUIDE)
SECTION = GUIDE.split("### Carrying the holes' witnesses in the skeleton", 1)[-1].split(
    "### After the skeleton merges", 1
)[0]

PRESENT = {
    "the file name, built from the assembly's": f"-partial.1{carried.SUFFIX}",
    "the marker that names the hole": "-- hole: h₁",
    "where the type comes from": "`expected_witness`",
    "what the second precheck says": "`holes[].witness`",
    "the own-Context import is left out": "leaving out its `import Nodes.«…».Context` line",
    "a failure refuses the whole partial": "refuses the whole partial",
    "the unknown-hole code": "`hole-witness-unknown`",
    "the old pin": "`400 hole-witness-unchecked`",
    "a hole without a file is as before": "created with its empty slot",
    "the hole is born ready": "is created `ready`",
    "the permitted-paths row": "`attempts/<timestamp>-<you>-partial.<n>.witness`",
    "the after-merge section knows": "`ready` if the skeleton carried its witness",
    # F07-T53
    "a file the gate has no place for": "`400 path-forbidden`, naming it",
    "what the old pin's precheck says": "carries `carried_witnesses`, whose `unchecked` lists them",
}


@pytest.mark.parametrize("what", sorted(PRESENT))
def test_the_guide_says(what: str) -> None:
    assert PRESENT[what] in FLAT, f"the guide does not say: {what}"


def test_the_section_sits_between_the_skeleton_and_its_holes() -> None:
    assert SECTION != GUIDE and "D-29 v3.24" in SECTION.splitlines()[0]
    assert GUIDE.index("## Skeletonization") < GUIDE.index("### Carrying the holes' witnesses")


def test_the_example_witness_is_one_the_grammar_reads() -> None:
    """The worked file in the guide is a carried witness by the gate's own reading: it names its
    hole, uses no ``sorry``, and its file names attach to the assembly beside them."""
    block = SECTION.split("```lean\n", 1)[1].split("```", 1)[0]
    assert carried.hole_named(block) == "h₁"
    names = re.findall(r"attempts/(\S+)", SECTION.split("```text\n", 1)[1].split("```", 1)[0])
    assembly, *witnesses = names
    files = {f"attempts/{name}": block for name in witnesses[:1]}
    read, problem = carried.read(f"attempts/{assembly}", files)
    assert problem is None and [w.hole for w in read] == ["h₁"]
    assert [carried.number_of(assembly, w) for w in witnesses] == [1, 2]


def test_every_refusal_the_guide_names_is_one_the_gate_gives() -> None:
    source = (ROOT / "gate" / "opn_gate" / "carried.py").read_text(encoding="utf-8") + (
        ROOT / "gate" / "opn_gate" / "steps" / "witness.py"
    ).read_text(encoding="utf-8")
    for code in ("unnamed", "duplicate", "sorry", "unattached", "unknown"):
        assert f'"hole-witness-{code}"' in source, code
    assert "`hole-witness-unnamed`, `-duplicate`, `-sorry`, `-unattached`" in FLAT
