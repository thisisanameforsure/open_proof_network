/-! F02 hazard fixture: no checker may fire. Divisors are syntactically non-zero; the subtraction
is on ℤ; the predecessor's argument is non-zero; the only literal comparison is against 0 (the
positivity idiom); the range's bound is a variable; every binder is used. -/

theorem OpnHazard.clean :
    ∀ (n : Nat) (z : Int),
      n / 2 ≤ n ∧ n % 2 < n + 2 ∧ (n + 1) / (n + 1) = 1 ∧ n / 2 ^ n ≤ n ∧
        z - 1 < z ∧ Nat.pred (n + 1) = n ∧ 0 < n + 1 ∧ (List.range n).length = n := by
  sorry
