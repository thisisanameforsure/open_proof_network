/-! F02 hazard fixture: divisions and moduli whose divisors are syntactically non-zero, and an
integer subtraction — no checker may fire. -/

theorem OpnHazard.clean :
    ∀ (n : Nat) (z : Int),
      n / 2 ≤ n ∧ n % 2 < 2 ∧ (n + 1) / (n + 1) = 1 ∧ n / 2 ^ n ≤ n ∧ z / (-3) = z / (-3) ∧
        z - 1 < z := by
  sorry
