import Mathlib

/-- 402-R5-b. Generalised-criterion certificate for n = 680: window prime 1327, excluded α 650 (prime 677 ≥ n/3 divides α·(p−α)). -/
theorem r5b_cert_680 : ∃ p : ℕ, p.Prime ∧ 680 < p ∧ p < 2 * 680 ∧ 2 * (2 * 680 - p) ≤ 680 + 2 ∧
    ∀ α : ℕ, α < 680 → p < α + 680 →
      (∃ q : ℕ, q.Prime ∧ 680 ≤ 3 * q ∧ q ∣ α * (p - α)) ∨
      (∀ x y : ℕ, x < y → x * y ∣ α → 680 * x ≤ α * y) := by
  refine ⟨1327, by norm_num, by norm_num, by norm_num, by norm_num, ?_⟩
  intro α h1 h2
  by_cases e650 : α = 650
  · left
    exact ⟨677, by norm_num, by norm_num, by subst e650; norm_num⟩
  right
  intro x y hxy hd
  obtain ⟨m, hm⟩ := hd
  by_contra hc
  have hc' : α * y < 680 * x := by omega
  have m0 : 0 < m := Nat.pos_of_ne_zero (by rintro rfl; simp at hm; omega)
  have b1 : 648 * x ≤ α * x := Nat.mul_le_mul_right _ (by omega)
  have b2 : α * (x + 1) ≤ α * y := Nat.mul_le_mul_left _ hxy
  have b2' : α * (x + 1) = α * x + α := by ring
  have b3 : 648 * y ≤ α * y := Nat.mul_le_mul_right _ (by omega)
  have b4 : x * (x + 1) ≤ x * y := Nat.mul_le_mul_left _ hxy
  have b4' : x * (x + 1) = x * x + x := by ring
  have b5 : x * y ≤ x * y * m := Nat.le_mul_of_pos_right _ m0
  have x1 : 21 ≤ x := by omega
  have x2 : x ≤ 25 := by
    by_contra h
    have : 26 * 26 ≤ x * x := Nat.mul_le_mul (by omega) (by omega)
    omega
  interval_cases x
  · have y2 : y ≤ 22 := by omega
    interval_cases y <;> omega
  · have y2 : y ≤ 23 := by omega
    interval_cases y <;> omega
  · have y2 : y ≤ 24 := by omega
    interval_cases y <;> omega
  · have y2 : y ≤ 25 := by omega
    interval_cases y <;> omega
  · have y2 : y ≤ 26 := by omega
    interval_cases y <;> omega
