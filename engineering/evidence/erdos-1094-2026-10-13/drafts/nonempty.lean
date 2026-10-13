import Mathlib

open scoped Nat

/-- The root's exceptional set is not empty: (7, 3) is in it, since C(7,3) = 35 = 5 · 7 and
5 > max (7 / 3) 3 = 3. -/
example : (7, 3) ∈ {(n, k) : ℕ × ℕ | 0 < k ∧ 2 * k ≤ n ∧ (n.choose k).minFac > max (n / k) k} := by
  show 0 < 3 ∧ 2 * 3 ≤ 7 ∧ (Nat.choose 7 3).minFac > max (7 / 3) 3
  rw [show Nat.choose 7 3 = 35 from rfl, show Nat.minFac 35 = 5 by norm_num]
  decide
