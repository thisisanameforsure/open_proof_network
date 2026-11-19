"""F28-T11 (bug B5, the 2026-11-19 agent run): the guide stops telling a prover to submit a
parent's assembly once its holes are proved.

Live: an agent proved the parent's last hole (graph #1508) and then, as ``gate/agents/AGENTS.md``
said, submitted the parent's ``Proof.lean`` "as a proof, the assembly with each ``sorry`` replaced
by its hole's theorem" (#1519). The post-merge closure sweep (D-12 v3.42) had already proved the
parent, so the file could only land as an alternate. The owner's ruling: the guide says the sweep
closes the parent once its holes are proved, and that a submitted assembly lands as an alternate.

Docs are tests (F10-Q3): read the guide's prose, fenced blocks excluded.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GUIDE = ROOT / "gate" / "agents" / "AGENTS.md"


def prose() -> str:
    kept: list[str] = []
    inside = False
    for line in GUIDE.read_text(encoding="utf-8").splitlines():
        if line.rstrip().startswith("```"):
            inside = not inside
            continue
        if not inside:
            kept.append(line)
    return " ".join(" ".join(kept).split())


def test_the_guide_no_longer_asks_for_the_assembly_after_the_holes() -> None:
    text = prose()
    for stale in (
        r"still needs its assemblies submitted",
        r"proving a decomposition's holes does not close the node",
        r"the parent can be finalized through them: submit the parent's `Proof\.lean`",
    ):
        assert not re.search(stale, text), f"the guide still says: {stale}"


def test_the_guide_says_the_sweep_closes_the_parent_and_an_assembly_is_an_alternate() -> None:
    text = prose()
    assert re.search(
        r"closure sweep (proves|joins)[^.]*\bparent\b|closure sweep proves the parent", text
    ), "the guide does not say the closure sweep proves the parent once its holes are proved"
    assert re.search(r"there is nothing left to submit|You submit nothing for that", text), (
        "the guide does not say the prover submits nothing to close the parent"
    )
    assert re.search(
        r"lands as (the parent's|an) alternate[^.]*attempts/<ts>-<pseudonym>-alternate\.lean", text
    ), "the guide does not say a later proof of a closed parent lands as an alternate, and where"
    assert re.search(r"`closure` note", text), "the guide does not name the precheck's note"
