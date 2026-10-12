"""F26-T7: the mutation operators against the first prototype's (R8; AC6's fast half).

No Lean: the mutants of each conjecture's reference are the text the prototype ran, class for
class, and the two D-11 classes it did not run are on top of them. The lean tier
(``test_review_mutants_lean.py``) runs them.
"""

from __future__ import annotations

import pytest
from review_support import PROTOTYPE, prototype_lean

from opn_gate import review_lean, review_mutants

#: The prototype's operators (``round.py``'s ``SWAPS`` and constants), as this module's classes.
PROTOTYPE_CLASSES = {"relation", "connective", "offset", "exponent", "product", "constant"}


def prototype_ops(m: review_mutants.Mutant) -> bool:
    """The prototype swapped ``<``/``≤`` only, not ``>``/``≥``."""
    return m.cls in PROTOTYPE_CLASSES and not m.label.startswith((">", "≥"))


def claim_of(text: str) -> str:
    """The prototype's mutant ``claim`` field is the whole ``def claim … := …``; compare the
    proposition after ``:=``."""
    return " ".join(text.split(":=", 1)[1].split())


@pytest.mark.parametrize(("conj", "count"), [("goldbach", 9), ("legendre", 15), ("oppermann", 19)])
def test_the_prototype_classes_give_the_prototype_mutants(conj: str, count: int) -> None:
    src = prototype_lean(conj, "human-ref")
    c = review_lean.prepare("c-00000001", src, ["prime"])
    assert isinstance(c, review_lean.Cand)
    found, capped = review_mutants.mutants(c, ["prime"])
    assert not capped
    ours = sorted(
        review_mutants._claim_line(m.source, ["prime"]) for m in found if prototype_ops(m)
    )
    theirs = sorted(claim_of(m["claim"]) for m in PROTOTYPE[conj]["mutants"])
    assert len(ours) == count
    assert ours == theirs


def test_the_added_classes_are_d11s() -> None:
    src = prototype_lean("goldbach", "human-ref")
    c = review_lean.prepare("c-00000001", src, ["prime"])
    assert isinstance(c, review_lean.Cand)
    found, _ = review_mutants.mutants(c, ["prime"])
    extra = [m for m in found if not prototype_ops(m)]
    assert {m.cls for m in extra} == {"hypothesis", "quantifier"}
    dropped = [
        review_mutants._claim_line(m.source, ["prime"]) for m in extra if m.cls == "hypothesis"
    ]
    assert "n % 2 = 0 → ∃ p, p ≤ n ∧ Prime p ∧ Prime (n - p)" in dropped


def test_a_mutant_changes_one_site_of_the_claim_only() -> None:
    src = prototype_lean("legendre", "human-ref")
    c = review_lean.prepare("c-00000001", src, ["prime"])
    assert isinstance(c, review_lean.Cand)
    found, _ = review_mutants.mutants(c, ["prime"])
    predicate = src.splitlines()[0]
    for m in found:
        assert m.source.splitlines()[0] == predicate  # the concept's predicate is never touched
        assert m.source != src


def test_the_cap() -> None:
    c = review_lean.prepare("c-00000001", prototype_lean("oppermann", "human-ref"), ["prime"])
    assert isinstance(c, review_lean.Cand)
    found, capped = review_mutants.mutants(c, ["prime"], cap=5)
    assert capped and len(found) == 5
