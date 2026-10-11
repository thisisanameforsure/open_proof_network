/-! F02 hazard fixture (F02-T9): the same division once the operand is cast off ℕ. `nat-div` must
stay quiet — the division is on ℤ (`int-trunc`'s business, and it fires), which is the shape the
checker exists to tell apart from a sum or quotient left over ℕ for want of an ascription. -/

theorem OpnHazard.nat_div_cast : ∀ n : Nat, ((n : Int) / 2) * 2 ≤ (n : Int) := by
  sorry
