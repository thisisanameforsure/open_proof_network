import Mathlib

/-- 402-R5-b. Generalised-criterion certificate for n = 61: window prime 113. -/
theorem r5b_cert_61 : ∃ p : ℕ, p.Prime ∧ 61 < p ∧ p < 2 * 61 ∧ 2 * (2 * 61 - p) ≤ 61 + 2 ∧
    ∀ α : ℕ, α < 61 → p < α + 61 →
      (∃ q : ℕ, q.Prime ∧ 61 ≤ 3 * q ∧ q ∣ α * (p - α)) ∨
      (∀ x y : ℕ, x < y → x * y ∣ α → 61 * x ≤ α * y) := by
  refine ⟨113, by norm_num, by norm_num, by norm_num, by norm_num, ?_⟩
  intro α h1 h2
  right
  intro x y hxy hd
  obtain ⟨m, hm⟩ := hd
  by_contra hc
  have hc' : α * y < 61 * x := by omega
  have m0 : 0 < m := Nat.pos_of_ne_zero (by rintro rfl; simp at hm; omega)
  have b1 : 53 * x ≤ α * x := Nat.mul_le_mul_right _ (by omega)
  have b2 : α * (x + 1) ≤ α * y := Nat.mul_le_mul_left _ hxy
  have b2' : α * (x + 1) = α * x + α := by ring
  have b3 : 53 * y ≤ α * y := Nat.mul_le_mul_right _ (by omega)
  have b4 : x * (x + 1) ≤ x * y := Nat.mul_le_mul_left _ hxy
  have b4' : x * (x + 1) = x * x + x := by ring
  have b5 : x * y ≤ x * y * m := Nat.le_mul_of_pos_right _ m0
  have x1 : 7 ≤ x := by omega
  have x2 : x ≤ 7 := by
    by_contra h
    have : 8 * 8 ≤ x * x := Nat.mul_le_mul (by omega) (by omega)
    omega
  interval_cases x
  · have y2 : y ≤ 8 := by omega
    interval_cases y <;> omega
