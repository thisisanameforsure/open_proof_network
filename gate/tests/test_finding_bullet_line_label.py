"""F29-T12 (B13, 2026-11-19 run): a hole's words may open on its focusing bullet's own line.

An agent wrote ``· -- label: …`` with the ``-- claim:`` and the ``have`` on the lines below,
inside the bullet, and was refused ``partial-unlabelled``; the same words with a plain comment on
the bullet line and the label on the next line passed. The bullet line is the first line of the
hole's comment block, so the scan reads it as one: in the gate (step 4, ``art.check``) and in
``labels.declarations``, which the service's pre-precheck refusal (F29-T3) reads too.
"""

from __future__ import annotations

from fakes import artifact_result

from opn_gate import labels
from opn_gate.steps import artifact as art

TWO_HOLES = [("right", "q", False), ("left", "p", False)]

ON_THE_BULLET = """theorem OpnProp.and_swap : ∀ (p q : Prop), p ∧ q → q ∧ p := by
  -- approach: split the goal and take each half from the hypothesis
  -- licence: CC-BY-4.0
  intro p q h
  refine ⟨?_, ?_⟩
  · -- label: the right half
    -- claim: $q$
    -- The second conjunct of the hypothesis.
    have right : q := sorry
    exact right
  · -- label: the left half
    -- claim: $p$
    have left : p := sorry
    exact left
"""

#: The form that already passed: prose on the bullet line, the label on the next line.
PROSE_ON_THE_BULLET = ON_THE_BULLET.replace(
    "  · -- label: the right half\n", "  · -- the right half\n    -- label: the right half\n"
)


def parsed() -> art.Artifact:
    return art.Artifact.of("partial", artifact_result(kind="partial", holes=TWO_HOLES).doc)


def test_a_label_on_the_bullet_line_is_read() -> None:
    d = labels.declarations(ON_THE_BULLET)
    assert d.holes["right"].label == "the right half"
    assert d.holes["right"].claim == "q"
    assert d.holes["right"].prose == "The second conjunct of the hypothesis."
    assert d.holes["left"].label == "the left half" and d.holes["left"].claim == "p"
    assert d.stray == ()


def test_step_4_takes_a_label_on_the_bullet_line() -> None:
    assert labels.problems(ON_THE_BULLET, hole_names=["right", "left"]) == []
    assert art.check(parsed(), partial_text=ON_THE_BULLET) == []


def test_prose_on_the_bullet_line_still_reads_as_prose() -> None:
    d = labels.declarations(PROSE_ON_THE_BULLET)
    assert d.holes["right"].label == "the right half"
    assert d.holes["right"].prose.startswith("the right half")
    assert art.check(parsed(), partial_text=PROSE_ON_THE_BULLET) == []


def test_the_bullet_line_closes_the_block() -> None:
    """The block stops at the bullet: a comment above the bullet belongs to the outer proof,
    so a ``-- label:`` there is not this hole's (it stays a stray line, as before)."""
    text = ON_THE_BULLET.replace(
        "  · -- label: the left half\n", "  -- label: an outer word\n  · -- label: the left half\n"
    )
    d = labels.declarations(text)
    assert d.holes["left"].label == "the left half"
    assert len(d.stray) == 1
