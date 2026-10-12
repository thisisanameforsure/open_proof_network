"""F20-T16 (Q21): a gloss that opens with its statement in display math, as the guidance now
asks, still gives the Problems row a sentence worth reading.

The row shows a gloss's first sentence (F20-R13, ``prose.first_sentence``). Its scanner toggled
on every ``$``, so the two dollars that open ``$$…$$`` cancelled out and a full stop inside the
display ended the "sentence" mid-formula: the row read ``$$ \\forall n \\ge 1,\\ n!``, raw TeX the
math renderer cannot close. Ruled here: when a gloss opens with a display block, the row shows
that block as inline math (the statement, which is what the row is for), rendered by the same
KaTeX path as every other ``$…$`` in a row.
"""

from __future__ import annotations

from opn_site import prose

GLOSS = (
    "$$\n\\forall n \\ge 1,\\ n! > 0.\n$$\n\n"
    "Here `n !` is `Nat.factorial`. For every n at least 1, n factorial is positive.\n"
)


def test_a_display_opening_is_the_rows_sentence_as_inline_math() -> None:
    assert prose.first_sentence(GLOSS) == "$\\forall n \\ge 1,\\ n! > 0.$"
    row = prose.inline_math(prose.first_sentence(GLOSS))
    assert row == '<span class="math">$\\forall n \\ge 1,\\ n! &gt; 0.$</span>'
    assert "$$" not in row


def test_display_math_on_one_line_and_with_prose_after_it_in_the_paragraph() -> None:
    assert prose.first_sentence("$$a + b = b + a$$ for all naturals.") == "$a + b = b + a$"


def test_a_dollar_pair_inside_a_prose_sentence_is_still_one_unit() -> None:
    """The scanner reads ``$$`` as one delimiter, so a stop inside display math in the middle of
    a sentence ends nothing; inline math and prose openings are unchanged."""
    text = "The sum $$x. y$$ is symmetric. More."
    assert prose.first_sentence(text) == "The sum $$x. y$$ is symmetric."
    assert prose.first_sentence("For $n \\ge 1$, it holds. More.") == "For $n \\ge 1$, it holds."
    assert prose.first_sentence("An empty display $$ $$ stays text.") == (
        "An empty display $$ $$ stays text."
    )
