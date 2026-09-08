/-! F02 hazard fixture: `int-trunc` and nothing else. False for odd `z`, which is the point; the
divisor is a literal so `div-zero` stays quiet. -/

theorem OpnHazard.int_trunc : ∀ z : Int, z / 2 * 2 = z := by
  sorry
