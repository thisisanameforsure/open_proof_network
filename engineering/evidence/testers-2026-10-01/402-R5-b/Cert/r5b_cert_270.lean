import Mathlib

/-- 402-R5-b. Generalised-criterion certificate for n = 270: window prime 523. -/
theorem r5b_cert_270 : ∃ p : ℕ, p.Prime ∧ 270 < p ∧ p < 2 * 270 ∧ 2 * (2 * 270 - p) ≤ 270 + 2 ∧
    ∀ α : ℕ, α < 270 → p < α + 270 →
      (∃ q : ℕ, q.Prime ∧ 270 ≤ 3 * q ∧ q ∣ α * (p - α)) ∨
      (∀ x y : ℕ, x < y → x * y ∣ α → 270 * x ≤ α * y) := by
  refine ⟨523, by norm_num, by norm_num, by norm_num, by norm_num, ?_⟩
  intro α h1 h2
  right
  intro x y hxy hd
  obtain ⟨m, hm⟩ := hd
  by_contra hc
  have hc' : α * y < 270 * x := by omega
  have m0 : 0 < m := Nat.pos_of_ne_zero (by rintro rfl; simp at hm; omega)
  have b1 : 254 * x ≤ α * x := Nat.mul_le_mul_right _ (by omega)
  have b2 : α * (x + 1) ≤ α * y := Nat.mul_le_mul_left _ hxy
  have b2' : α * (x + 1) = α * x + α := by ring
  have b3 : 254 * y ≤ α * y := Nat.mul_le_mul_right _ (by omega)
  have b4 : x * (x + 1) ≤ x * y := Nat.mul_le_mul_left _ hxy
  have b4' : x * (x + 1) = x * x + x := by ring
  have b5 : x * y ≤ x * y * m := Nat.le_mul_of_pos_right _ m0
  have x1 : 16 ≤ x := by omega
  have x2 : x ≤ 15 := by
    by_contra h
    have : 16 * 16 ≤ x * x := Nat.mul_le_mul (by omega) (by omega)
    omega
  omega
