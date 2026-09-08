/-! F02 hazard fixture: `div-zero` and nothing else. The divisor `b` may be zero. -/

theorem OpnHazard.div_zero : ∀ a b : Nat, a / b * b ≤ a := by
  sorry
