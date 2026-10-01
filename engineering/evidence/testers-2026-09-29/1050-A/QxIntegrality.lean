import Mathlib

theorem erdos_1050_gauss_binom_two_int (n k : ℕ) :
    ∃ z : ℤ, (z : ℚ) = ∏ i ∈ Finset.range k, ((2 : ℚ) ^ (n - i) - 1) / ((2 : ℚ) ^ (i + 1) - 1) := by
  sorry

theorem qx_int (Qc : ℕ → ℕ → ℚ)
    (hQc : Qc = fun (n k : ℕ) =>
      ((-1 : ℚ) ^ k * (2 : ℚ) ^ (k * (k - (1 : ℕ)) / (2 : ℕ)) *
          ∏ i ∈ Finset.range k, ((2 : ℚ) ^ (n - i) - (1 : ℚ)) / ((2 : ℚ) ^ (i + (1 : ℕ)) - (1 : ℚ))) *
        ∏ i ∈ Finset.range n, ((2 : ℚ) ^ ((2 : ℕ) * n - k - i) - (1 : ℚ)) / ((2 : ℚ) ^ (i + (1 : ℕ)) - (1 : ℚ)))
    (n : ℕ) :
    ∃ z : ℤ, (z : ℚ) = (2 : ℚ) ^ (n * (n + 1) / 2) *
      ∑ k ∈ Finset.range (n + (1 : ℕ)), Qc n k * ((3 : ℚ) / (2 : ℚ) ^ n) ^ k := by
  have hterm : ∀ k ∈ Finset.range (n + 1), ∃ z : ℤ,
      (z : ℚ) = (2 : ℚ) ^ (n * (n + 1) / 2) * (Qc n k * ((3 : ℚ) / (2 : ℚ) ^ n) ^ k) := by
    intro k hk
    have hkn : k ≤ n := Nat.lt_succ_iff.mp (Finset.mem_range.mp hk)
    obtain ⟨a, ha⟩ := erdos_1050_gauss_binom_two_int n k
    obtain ⟨b, hb⟩ := erdos_1050_gauss_binom_two_int (2 * n - k) n
    obtain ⟨m, rfl⟩ := Nat.exists_eq_add_of_le hkn
    have hexp : (k + m) * (k + m + 1) / 2 + k * (k - 1) / 2 = m * (m + 1) / 2 + (k + m) * k := by
      have e1 : 2 * ((k + m) * (k + m + 1) / 2) = (k + m) * (k + m + 1) :=
        Nat.two_mul_div_two_of_even (Nat.even_mul_succ_self _)
      have e2 : 2 * (k * (k - 1) / 2) = k * (k - 1) :=
        Nat.two_mul_div_two_of_even (Nat.even_mul_pred_self _)
      have e3 : 2 * (m * (m + 1) / 2) = m * (m + 1) :=
        Nat.two_mul_div_two_of_even (Nat.even_mul_succ_self _)
      rcases k with _ | j
      · simp
      · simp only [Nat.add_sub_cancel] at e2 ⊢
        nlinarith [e1, e2, e3]
    refine ⟨(-1) ^ k * 3 ^ k * 2 ^ (m * (m + 1) / 2) * a * b, ?_⟩
    have hpow : (2 : ℚ) ^ ((k + m) * (k + m + 1) / 2) * (2 : ℚ) ^ (k * (k - 1) / 2) =
        (2 : ℚ) ^ (m * (m + 1) / 2) * ((2 : ℚ) ^ (k + m)) ^ k := by
      rw [← pow_add, ← pow_mul, ← pow_add, hexp]
    have h2 : ((2 : ℚ) ^ (k + m)) ≠ 0 := by positivity
    rw [hQc]
    simp only []
    rw [← ha, ← hb]
    push_cast
    rw [div_pow, mul_div_assoc']
    field_simp
    linear_combination -(a : ℚ) * b * hpow
  choose! g hg using hterm
  refine ⟨∑ k ∈ Finset.range (n + 1), g k, ?_⟩
  push_cast
  rw [Finset.mul_sum]
  exact Finset.sum_congr rfl (fun k hk => hg k hk)
