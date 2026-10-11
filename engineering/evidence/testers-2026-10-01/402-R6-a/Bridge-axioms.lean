import Mathlib

/-- 402-R5-b. The simple window condition (2n − p)² ≤ n of 402-R4-c implies the hypotheses of
r5b_gen_criterion (with no excluded shape), so the generalised criterion subsumes the simple one. -/
theorem r5b_bridge : ∀ n p : ℕ, n < p → p < 2 * n → (2 * n - p) * (2 * n - p) ≤ n →
    2 * (2 * n - p) ≤ n + 2 ∧
    ∀ α : ℕ, α < n → p < α + n →
      (∃ q : ℕ, q.Prime ∧ n ≤ 3 * q ∧ q ∣ α * (p - α)) ∨
      (∀ x y : ℕ, x < y → x * y ∣ α → n * x ≤ α * y) := by
  intro n p h1 h2 h3
  generalize hk : 2 * n - p = k at *
  constructor
  · rcases Nat.lt_or_ge k 3 with h | h
    · omega
    · have : 3 * k ≤ k * k := Nat.mul_le_mul_right _ h
      omega
  · intro α hα1 hα2
    right
    intro x y hxy hd
    by_contra hc
    have h : α * y < n * x := by omega
    have α0 : 0 < α := by omega
    have hx : x * y ≤ α := Nat.le_of_dvd α0 hd
    obtain ⟨s, rfl⟩ : ∃ s, n = α + s := ⟨n - α, by omega⟩
    have hs : s < k := by omega
    have a1 : α * (x + 1) ≤ α * y := Nat.mul_le_mul_left _ hxy
    have a2 : α < s * x := by nlinarith
    have a3 : x * (x + 1) ≤ x * y := Nat.mul_le_mul_left _ hxy
    have a4 : x + 1 < s := by
      by_contra hc
      have : s * x ≤ (x + 1) * x := Nat.mul_le_mul_right _ (by omega)
      nlinarith
    have a5 : (s + 1) * (s + 1) ≤ k * k := Nat.mul_le_mul hs hs
    have a6 : s * x ≤ s * s := Nat.mul_le_mul_left _ (by omega)
    nlinarith

#print axioms r5b_bridge
