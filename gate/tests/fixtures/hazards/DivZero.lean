/-! F02 hazard fixture: `div-zero` and nothing else. The divisor `b` may be zero. Modulo rather
than division since F02-T9, because every `/` on ℕ is `nat-div`'s as well; `a % b` asks the same
question of the divisor (`a % 0 = a`) and nothing else. -/

theorem OpnHazard.div_zero : ∀ a b : Nat, a % b ≤ a := by
  sorry
