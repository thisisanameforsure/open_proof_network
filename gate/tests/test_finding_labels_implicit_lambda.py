# ruff: noqa: RUF001 — the fixture is Lean source, with its double-struck letters
"""Finding labels-implicit-lambda (testers 2026-11-24, Reed's conjecture): a labelled partial was
refused ``partial-unlabelled`` at step 4, after the service had let its precheck run.

Each hole's type began with implicit and instance binders (``∀ {V : Type} [Fintype V] …``), so
the tester bound it ``:= no_implicit_lambda% sorry`` (a plain ``sorry`` is elaborated under the
binders' lambdas and step 4 calls it ``hole-unnamed``). The label scan's hole shape knew only
``:= sorry`` and ``:= by sorry``: the service's pre-flight saw no hole and asked for no label,
while the gate, holding the extractor's three hole names to the rule, could not find the label
blocks that sat above them. The two sides disagreed about a partial whose words were all there.
"""

from __future__ import annotations

from opn_gate import labels

PARTIAL = """\
theorem Opn.reed : True := by
  -- approach: greedy, then Brooks, then the open core
  -- licence: CC-BY-4.0
  -- label: greedy bound
  -- claim: $\\chi(G) \\le \\Delta(G) + 1$
  have h_greedy : ∀ {V : Type} [Fintype V] (n : ℕ), n ≤ n + 1 := no_implicit_lambda% sorry
  · -- label: Brooks
    -- claim: $\\chi(G) \\le \\Delta(G)$
    have h_brooks : ∀ {V : Type} [Fintype V], True :=
      no_implicit_lambda% sorry
  -- label: the open core
  -- claim: $2\\chi \\le \\omega + \\Delta + 2$
  have h_core : ∀ {V : Type}, True := by no_implicit_lambda% sorry
  trivial
"""

NAMES = ["h_greedy", "h_brooks", "h_core"]


def test_the_scan_sees_holes_bound_without_implicit_lambdas() -> None:
    """The service's pre-flight reads the holes from the text alone."""
    assert sorted(labels.declarations(PARTIAL).holes) == sorted(NAMES)


def test_labelled_holes_meet_the_rule_with_the_extractors_names() -> None:
    """The gate's reading, at step 4."""
    assert labels.problems(PARTIAL, hole_names=NAMES) == []


def test_an_unlabelled_one_is_still_named_by_the_preflight() -> None:
    """The point of the pre-flight: a missing label is caught before a precheck is spent."""
    text = PARTIAL.replace("  -- label: the open core\n", "")
    found = labels.problems(text)
    assert [(p.code, p.hole) for p in found] == [("label", "h_core")]


def test_a_have_bound_to_something_else_is_not_a_hole() -> None:
    text = PARTIAL.replace(
        "no_implicit_lambda% sorry\n  trivial", "no_implicit_lambda% trivial\n  trivial"
    )
    assert "h_core" not in labels.declarations(text).holes
