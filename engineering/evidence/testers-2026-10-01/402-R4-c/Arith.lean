import Mathlib

/-- 402-R4-c. Arithmetic heart of the rectangle lemma: two coprime divisors of α whose ratio is
squeezed between α/n and n/α are equal (hence both 1), when α is within k of n and k² ≤ n. -/
theorem r4c_arith (n k α e1 e2 : ℕ) (hk : k * k ≤ n) (hα : n < α + k)
    (he : e1 * e2 ≤ α) (h1 : α * e1 < n * e2) (h4 : α * e2 < n * e1) : e1 = e2 := by
  have key : ∀ x y : ℕ, x < y → x * y ≤ α → α * y < n * x → False := by
    intro x y hxy hx h
    have hαn : α ≤ n := by
      by_contra hc
      have : n * x ≤ α * y := Nat.mul_le_mul (by omega) (by omega)
      omega
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
  rcases Nat.lt_trichotomy e1 e2 with h | h | h
  · exact (key e1 e2 h he h4).elim
  · exact h
  · exact (key e2 e1 h (by rwa [Nat.mul_comm]) h1).elim
