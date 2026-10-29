# ruff: noqa: RUF001, RUF002 — the fixtures are Lean source and mathematics, with their letters
"""F29-T1 (R1–R5; D-3, D-12, D-25 v3.44): labels, claims and approaches.

The partial's header grammar (``opn_gate.labels.declarations``), what it is missing
(``problems``), a route's approach with its fallbacks (``approach_of``), the claim a gloss body
opens with (``claim_of``), and a node's label from the record (``label_of``). Pure functions over
text; the products test proves they reach ``graph.json``.
"""

from __future__ import annotations

import pytest

from opn_gate import labels

PARTIAL = """import Mathlib
import Nodes.«t--h2».Context

theorem t__h2 : P := by
  -- annex: 6c7d3be4efeecc319f87dc55a1638245a01739d8f2167e05b11ba9d9d31853b7
  -- approach: Baker–Harman–Pintz short-interval primes, then van Doorn–Tang
  -- licence: CC-BY-4.0
  -- label: BHP prime count
  -- claim: $\\pi(k + k^{21/40}) - \\pi(k) \\ge C k^{21/40} / \\log k$
  -- Baker, Harman and Pintz (2001): for large k the interval holds primes.
  have h_bhp : ∃ C : ℝ, 0 < C ∧ ∃ k₀ : ℕ, ∀ k : ℕ, k₀ ≤ k →
      C * (k : ℝ) ^ ((21 : ℝ) / 40) / Real.log k ≤ f k := by
    sorry
  -- label: the thin strip above k²
  -- claim: $k^2 \\le n < k(k + 3k^{21/40}) \\Rightarrow k \\le K$
  have h_strip : ∃ K : ℕ, ∀ n k : ℕ, k * k ≤ n → k ≤ K := sorry
  -- the assembly
  have hasym : ∃ k₁ : ℕ, ∀ k : ℕ, k₁ ≤ k → g k := by
    exact ⟨0, fun _ _ => trivial⟩
  exact combine h_bhp h_strip hasym
"""


def test_declarations_read_the_approach_the_licence_and_each_hole() -> None:
    d = labels.declarations(PARTIAL)
    assert d.approach == "Baker–Harman–Pintz short-interval primes, then van Doorn–Tang"
    assert d.licence == "CC-BY-4.0"
    assert list(d.holes) == ["h_bhp", "h_strip"], "a proved have is not a hole"
    bhp = d.holes["h_bhp"]
    assert bhp.label == "BHP prime count"
    assert bhp.claim == "\\pi(k + k^{21/40}) - \\pi(k) \\ge C k^{21/40} / \\log k"
    assert bhp.prose == "Baker, Harman and Pintz (2001): for large k the interval holds primes."
    strip = d.holes["h_strip"]
    assert strip.label == "the thin strip above k²"
    assert strip.prose == ""


def test_a_complete_partial_has_no_problems() -> None:
    assert labels.problems(PARTIAL) == []
    assert labels.problems(PARTIAL, hole_names=["h_bhp", "h_strip"]) == []


def test_each_missing_line_is_named_with_its_hole() -> None:
    text = PARTIAL.replace("  -- label: BHP prime count\n", "").replace(
        "  -- approach: Baker–Harman–Pintz short-interval primes, then van Doorn–Tang\n", ""
    )
    found = labels.problems(text)
    assert [p.code for p in found] == ["approach", "label"]
    assert found[1].hole == "h_bhp"
    assert "-- label:" in found[1].message and "h_bhp" in found[1].message


def test_the_extractors_hole_names_are_the_ones_held_to_the_rule() -> None:
    # The service scans the text; the gate has the extractor's names (step 4) and asks for
    # those: a hole the scan could not see is still refused, by name.
    found = labels.problems(PARTIAL, hole_names=["h_bhp", "h_strip", "h_other"])
    assert [(p.code, p.hole) for p in found] == [("label", "h_other"), ("claim", "h_other")]


@pytest.mark.parametrize(
    ("line", "code"),
    [
        ("  -- label: " + "x" * 61 + "\n", "label-long"),
        ("  -- label: $x$\n", "label-form"),
        ("  -- claim: no dollars\n", "claim-form"),
        ("  -- claim: $$\n", "claim-form"),
    ],
)
def test_a_malformed_line_is_refused_by_name(line: str, code: str) -> None:
    text = (
        PARTIAL.replace("  -- label: BHP prime count\n", line)
        if "label" in line
        else (
            PARTIAL.replace(
                "  -- claim: $\\pi(k + k^{21/40}) - \\pi(k) \\ge C k^{21/40} / \\log k$\n", line
            )
        )
    )
    found = labels.problems(text)
    assert [p.code for p in found] == [code], found
    assert found[0].hole == "h_bhp"


@pytest.mark.parametrize(
    "line",
    [
        # testers 2026-10-27 (A's F3): prose before the notation
        "  -- claim: a left-half solution $(n,k)$ of $\\binom{n}{k}=a$ has $\\log a \\le k$\n",
        # B's F2: prose after the closing dollar
        "  -- claim: $A$ holds for every collision\n",
    ],
)
def test_a_claim_with_prose_outside_its_dollars_says_where_the_prose_goes(line: str) -> None:
    """The rule is that the claim begins and ends with a dollar sign. Two testers read the
    guide's `$<the hole in notation>$` as "notation somewhere in the line" and paid a refusal
    each; the refusal must say the rule, and where the prose belongs."""
    text = PARTIAL.replace(
        "  -- claim: $\\pi(k + k^{21/40}) - \\pi(k) \\ge C k^{21/40} / \\log k$\n", line
    )
    found = labels.problems(text)
    assert [p.code for p in found] == ["claim-form"], found
    assert "begin and end with a dollar sign" in found[0].message
    assert "other comment lines" in found[0].message


def test_a_licence_outside_the_accepted_set_is_refused() -> None:
    text = PARTIAL.replace("-- licence: CC-BY-4.0", "-- licence: WTFPL")
    assert [p.code for p in labels.problems(text)] == ["licence-invalid"]
    text = PARTIAL.replace("  -- licence: CC-BY-4.0\n", "")
    assert [p.code for p in labels.problems(text)] == ["licence"]


def test_a_claim_may_span_lines_until_the_closing_dollar() -> None:
    text = PARTIAL.replace(
        "  -- claim: $\\pi(k + k^{21/40}) - \\pi(k) \\ge C k^{21/40} / \\log k$\n",
        "  -- claim: $\\pi(k + k^{21/40}) - \\pi(k)\n  --   \\ge C k^{21/40} / \\log k$\n",
    )
    d = labels.declarations(text)
    assert d.holes["h_bhp"].claim == "\\pi(k + k^{21/40}) - \\pi(k) \\ge C k^{21/40} / \\log k"
    assert labels.problems(text) == []


# --- approach_of: the declared line, then the fallbacks for older partials (R4) ----------------

OLD_PARTIAL = """theorem t__h3 : P := by
  -- annex: 6c7d3be4efeecc319f87dc55a1638245a01739d8f2167e05b11ba9d9d31853b7
  -- Skeleton of Granville–Ramaré, Mathematika 43 (1996), Theorem 8:
  -- the sieve bound, then the Chebyshev estimate.
  have h_els : A := sorry
  exact h_els
"""

ANNEX = """---
schema: annex/v2
---
The Granville–Ramaré sieve gives the bound directly. A second paragraph says more.
"""


def test_approach_is_the_declared_line_first() -> None:
    assert labels.approach_of(PARTIAL, annex=ANNEX) == (
        "Baker–Harman–Pintz short-interval primes, then van Doorn–Tang"
    )


def test_an_older_partial_takes_its_leading_comment_paragraph() -> None:
    assert labels.approach_of(OLD_PARTIAL, annex=ANNEX) == (
        "Skeleton of Granville–Ramaré, Mathematika 43 (1996), Theorem 8: the sieve bound, then "
        "the Chebyshev estimate."
    )


def test_then_the_annexs_first_sentence_then_nothing() -> None:
    bare = (
        "theorem t__h3 : P := by\n  -- annex: " + "a" * 64 + "\n  have h : A := sorry\n  exact h\n"
    )
    assert labels.approach_of(bare, annex=ANNEX) == (
        "The Granville–Ramaré sieve gives the bound directly."
    )
    assert labels.approach_of(bare, annex=None) is None


def test_an_approach_is_cut_to_the_schemas_width() -> None:
    long = OLD_PARTIAL.replace("the sieve bound, then the Chebyshev estimate.", "y " * 400)
    found = labels.approach_of(long, annex=None)
    assert found is not None and len(found) <= labels.APPROACH_MAX and found.endswith("…")


# --- claim_of and label_of (R3; D-3 v3.44) -----------------------------------------------------


def test_claim_of_is_the_opening_display_without_its_delimiters() -> None:
    assert labels.claim_of("$$\\sum_{p} \\frac{1}{p} = \\infty$$\n\nThe primes diverge.") == (
        "\\sum_{p} \\frac{1}{p} = \\infty"
    )
    assert labels.claim_of("$x = 1$ inline opens it") == "x = 1"
    assert labels.claim_of("The primes diverge: $$x$$") is None
    assert labels.claim_of("") is None


def test_label_of_prefers_the_gloss_then_the_hole_then_the_target_then_the_id() -> None:
    assert labels.label_of("t--h1", gloss_label="Prime count", hole_name="h_bhp") == (
        "Prime count",
        "gloss",
    )
    assert labels.label_of("t--h1", gloss_label=None, hole_name="h_bhp") == ("h_bhp", "hole")
    assert labels.label_of("t", gloss_label=None, hole_name=None, title="Erdős 1094") == (
        "Erdős 1094",
        "target",
    )
    assert labels.label_of("t--v1", gloss_label=None, hole_name=None) == ("t--v1", "id")


def test_a_root_takes_the_head_of_a_sentence_title_or_keeps_its_id() -> None:
    # Live titles read "Erdős problem 1094: For all $n\\ge 2k$ …": a statement, not a name.
    sentence = (
        "Erdős problem 1094: For all $n\\ge 2k$ the least prime factor of $\\binom{n}{k}$ is small."
    )
    assert labels.label_of("erdos-1094", gloss_label=None, hole_name=None, title=sentence) == (
        "Erdős problem 1094",
        "target",
    )
    long_plain = "x" * 61
    assert labels.label_of("t", gloss_label=None, hole_name=None, title=long_plain) == ("t", "id")
    assert labels.label_of("t", gloss_label=None, hole_name=None, title="$x$: y") == ("t", "id")
