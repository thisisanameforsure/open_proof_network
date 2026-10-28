# ruff: noqa: RUF001 — the candidate and its variants are Lean source, double-struck letters
"""F26-T22: a surviving mutant's question says what changed (Q24).

erdos-257's review (2026-10-14) raised eight questions, every one the same sentence: "A variant
of the statement agrees with it on every small case checked. Is there a case on which the
conjecture and this variant should differ?" The claim is a closed proposition, so no small case
was ever checked, and nothing in the question or on the page said which variant it was. The
variant is recoverable: each mutant exhibit's ``detail`` carries the mutant's label and class, and
``mutants`` over the candidate's Lean rebuilds the mutant the label names. So the question names
its change and class (and, for a closed claim, why no case could tell them apart), and the page
shows the variant beside the statement, for the eight questions already on the record too.
"""

from __future__ import annotations

from pathlib import Path

from review_support import Model, ReviewFake, legendre, make_graph, prototype_lean
from test_review_job import run_job
from test_review_questions import questions

from opn_gate import review_lean, review_mutants

#: erdos-257's candidate c-f0a2c098 as filed, licence header and doc comment shortened: the
#: labels' offsets count from the claim's proposition, so nothing above the theorem moves them
#: (the theorem itself is byte for byte: its whitespace is in the offsets).
ERDOS_257 = """import Mathlib

/-! Erdős problem 257. -/
theorem Opn.erdos_257 :
    ∀ (A : Set ℕ), A.Infinite →
    Irrational (∑' n : A, (1 : ℝ) / (2 ^ n.1 - 1)) := by
  sorry
"""
STATEMENT = "∀ (A : Set ℕ), A.Infinite → Irrational (∑' n : A, (1 : ℝ) / (2 ^ n.1 - 1))"

#: The eight live exhibits' ``detail``, verbatim (graph targets/erdos-257/review/exhibits/).
TAIL = ": every test passes and no case checked tells it from the representative"
LIVE = {
    "∀ → ∃ at 0 (quantifier)": (
        "∃ (A : Set ℕ), A.Infinite → Irrational (∑' n : A, (1 : ℝ) / (2 ^ n.1 - 1))"
    ),
    "1 → 0 at 55 (constant)": (
        "∀ (A : Set ℕ), A.Infinite → Irrational (∑' n : A, (0 : ℝ) / (2 ^ n.1 - 1))"
    ),
    "1 → 2 at 55 (constant)": (
        "∀ (A : Set ℕ), A.Infinite → Irrational (∑' n : A, (2 : ℝ) / (2 ^ n.1 - 1))"
    ),
    "2 → 1 at 65 (constant)": (
        "∀ (A : Set ℕ), A.Infinite → Irrational (∑' n : A, (1 : ℝ) / (1 ^ n.1 - 1))"
    ),
    "2 → 3 at 65 (constant)": (
        "∀ (A : Set ℕ), A.Infinite → Irrational (∑' n : A, (1 : ℝ) / (3 ^ n.1 - 1))"
    ),
    "1 → 0 at 75 (constant)": (
        "∀ (A : Set ℕ), A.Infinite → Irrational (∑' n : A, (1 : ℝ) / (2 ^ n.1 - 0))"
    ),
    "1 → 2 at 75 (constant)": (
        "∀ (A : Set ℕ), A.Infinite → Irrational (∑' n : A, (1 : ℝ) / (2 ^ n.1 - 2))"
    ),
    "`A.Infinite →` dropped at 14 (hypothesis)": (
        "∀ (A : Set ℕ), Irrational (∑' n : A, (1 : ℝ) / (2 ^ n.1 - 1))"
    ),
}


def test_a_live_exhibits_detail_gives_back_its_label_and_class() -> None:
    assert review_mutants.label_of("∀ → ∃ at 0 (quantifier)" + TAIL) == ("∀ → ∃ at 0", "quantifier")
    assert review_mutants.label_of("`A.Infinite →` dropped at 14 (hypothesis)" + TAIL) == (
        "`A.Infinite →` dropped at 14",
        "hypothesis",
    )
    # the other results' details carry the label the same way
    assert review_mutants.label_of("< → ≤ at 3 (relation): caught by test t-1 at n = 2") == (
        "< → ≤ at 3",
        "relation",
    )
    # a class the stage does not have, or no class at all, is not a mutant label
    assert review_mutants.label_of("mutant: or for and in the goal") is None
    assert review_mutants.label_of("x at 1 (colour): every test passes") is None


def test_each_live_label_rebuilds_its_variant_from_the_candidate() -> None:
    assert review_mutants._claim_line(ERDOS_257, []) == STATEMENT
    for head, expected in LIVE.items():
        parsed = review_mutants.label_of(head + TAIL)
        assert parsed is not None, head
        assert review_mutants.variant(ERDOS_257, [], parsed[0]) == expected, head


def test_a_label_no_mutant_carries_rebuilds_nothing() -> None:
    assert review_mutants.variant(ERDOS_257, [], "∃ → ∀ at 0") is None
    assert review_mutants.variant(ERDOS_257, [], "1 → 0 at 56") is None
    assert review_mutants.variant("not lean at all", [], "∀ → ∃ at 0") is None


def test_a_case_free_question_names_the_change_and_its_class() -> None:
    q = review_mutants.case_free_question("`A.Infinite →` dropped at 14", "hypothesis", closed=True)
    assert "`A.Infinite →` dropped" in q and "hypothesis" in q
    assert " at 14" not in q  # the offset is the page's to show, as the variant itself
    assert "closed" in q and "small case checked" not in q  # no case was checked: say why
    assert q.endswith("?")
    open_ = review_mutants.case_free_question("< → ≤ at 3", "relation", closed=False)
    assert "< → ≤" in open_ and "relation" in open_ and "every small case checked" in open_
    # yes/no by construction: an answer's first word is what the job reads
    assert open_.split("?")[0].split(". ")[-1].startswith("Does")


def test_the_job_asks_the_case_free_question_with_the_change(tmp_path: Path) -> None:
    """A mutant that every test passes, that no case tells apart and that is not proved
    equivalent raises the case-free question, now naming its change."""
    graph, ids = make_graph(
        tmp_path,
        candidates={"faithful": prototype_lean("legendre", "human-ref")},
        people=("faithful",),
    )
    a = ids["faithful"]
    cand = review_lean.prepare(a, prototype_lean("legendre", "human-ref"), ["prime"])
    assert isinstance(cand, review_lean.Cand)
    found, _ = review_mutants.mutants(cand, ["prime"])
    same = next(i for i, m in enumerate(found) if m.label.startswith("< → ≤"))
    fake = ReviewFake(models={a: Model(legendre())}, mutant_models={same: Model(legendre())})
    run_job(graph, fake, tmp_path)
    (q,) = [q for q in questions(graph) if q["raised_by"]["kind"] == "mutant"]
    assert "< → ≤" in q["question"] and "relation" in q["question"], q["question"]
