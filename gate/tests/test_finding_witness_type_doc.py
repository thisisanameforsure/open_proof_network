"""F01: the expected-witness-type metaprogram's own doc says what it computes.

Tester finding 2026-09-27: ``WitnessType.lean``'s module doc said "a statement with no Prop
binders gets `True`", and an agent read that as the whole witness type of a statement with two
natural-number binders and no hypotheses. The code quantifies every data binder existentially
over the conjunction, so that statement's expected type is ``True`` under two existentials; plain
``True`` is the answer only for a statement with no binders at all. The guide already says so
(the "The witness, exactly" paragraph); this holds the module doc and the guide to it.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "gate" / "lean" / "OpnGate" / "WitnessType.lean"
GUIDE = ROOT / "gate" / "agents" / "AGENTS.md"


def module_doc() -> str:
    found = re.search(r"/-!(.*?)-/", MODULE.read_text(encoding="utf-8"), re.S)
    assert found is not None
    return " ".join(found.group(1).split())


def test_the_module_doc_does_not_say_no_prop_binders_means_true() -> None:
    assert "no Prop binders gets `True`" not in module_doc()


def test_the_module_doc_says_data_binders_stay_existential() -> None:
    doc = module_doc()
    nat = "\N{DOUBLE-STRUCK CAPITAL N}"
    assert f"∃ (n : {nat}) (k : {nat}), True" in doc
    assert "no binders at all" in doc


def test_the_guide_says_the_same() -> None:
    guide = " ".join(GUIDE.read_text(encoding="utf-8").split())
    assert "`∀ n : Nat, C` wants `∃ n : Nat, True`" in guide
    assert "no binders at all wants plain `True`" in guide
    assert "no Prop binders gets `True`" not in guide
