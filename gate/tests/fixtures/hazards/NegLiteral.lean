/-! F02 hazard fixture: a negative literal divisor on ℤ. `div-zero` must stay quiet (`-3` is
syntactically non-zero); `int-trunc` fires once, because ℤ division rounds. -/

theorem OpnHazard.neg_literal : ∀ z : Int, z / (-3) = z / (-3) := by
  sorry
