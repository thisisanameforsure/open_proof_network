/-! F02 hazard fixture (F02-T9): `nat-div` and nothing else. `n / 2` over ℕ is the floor of the
quotient, so `n / 2 * 2 ≤ n` holds and `n / 2 * 2 = n` fails for odd `n`; the divisor is a literal,
so `div-zero` stays quiet, and the type is ℕ, so `int-trunc` does. -/

theorem OpnHazard.nat_div : ∀ n : Nat, n / 2 * 2 ≤ n := by
  sorry
