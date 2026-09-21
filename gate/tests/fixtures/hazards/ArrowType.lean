/-! F02 hazard fixture (F02-T8): a function type is not a quantified statement. `Nat → Int` is a
`∀` whose variable nothing mentions, and `unused-binder` reported it as one, under the name the
elaborator gave its anonymous binder. Every variable this statement quantifies is used. -/

theorem OpnHazard.arrow_type : ∃ a b : Nat → Int, ∀ n : Nat, a n = b n := by
  sorry
