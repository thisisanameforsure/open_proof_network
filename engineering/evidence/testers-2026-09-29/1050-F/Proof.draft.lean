import Mathlib

/-- erdos-1050, hole hden (erdos-1050--h1-v2--h3), ingredient 2, odd half, of annex 4670684d2f0d
on that node. Every denominator 2^(k - j) - 1 with 1 ≤ k - j ≤ n divides
M_n = ∏_{n/2 < m ≤ n} (2^m - 1), because m has the multiple m * (n / m) in (n/2, n]. Hence M_n
clears the inner sum p_k(n) = ∑_{j ≤ k} Qc n j / (2^(k - j) - 1) of `Aq` in h3 for any integer
coefficients (Qc n j is one by ingredient 1, spec-440db0f9). The j = k term divides by 2^0 - 1 = 0
and is 0 in ℚ, as in h3. The 2-adic half of ingredient 2 (v2(p_k(n)) ≥ k(k-1)/2) is not claimed. -/
theorem erdos_1050_upper_half_mersenne_clears (n k : ℕ) (hk : k ≤ n) (c : ℕ → ℤ) :
    ∃ z : ℤ, (z : ℚ) = (∏ m ∈ Finset.Ioc (n / 2) n, ((2 : ℚ) ^ m - 1)) *
      ∑ j ∈ Finset.range (k + 1), (c j : ℚ) / ((2 : ℚ) ^ (k - j) - 1) := by
  -- every 2^m - 1 with 1 ≤ m ≤ n divides the product over the upper half (n/2, n]
  have key : ∀ m : ℕ, 1 ≤ m → m ≤ n →
      ((2 : ℤ) ^ m - 1) ∣ ∏ i ∈ Finset.Ioc (n / 2) n, ((2 : ℤ) ^ i - 1) := by
    intro m hm1 hmn
    have ht1 : 1 ≤ n / m := (Nat.one_le_div_iff (by omega)).2 hmn
    have hle : m * (n / m) ≤ n := Nat.mul_div_le n m
    have hlt : n < m * (n / m) + m := by
      have := Nat.lt_mul_div_succ n (show 0 < m by omega)
      rw [Nat.mul_succ] at this
      exact this
    have hmem : m * (n / m) ∈ Finset.Ioc (n / 2) n := by
      rw [Finset.mem_Ioc]
      constructor
      · have : m ≤ m * (n / m) := Nat.le_mul_of_pos_right m (by omega)
        omega
      · exact hle
    have h1 : ((2 : ℤ) ^ m - 1) ∣ (2 : ℤ) ^ (m * (n / m)) - 1 := by
      have := sub_dvd_pow_sub_pow ((2 : ℤ) ^ m) 1 (n / m)
      rwa [one_pow, ← pow_mul] at this
    exact h1.trans (Finset.dvd_prod_of_mem _ hmem)
  refine ⟨∑ j ∈ Finset.range (k + 1),
      c j * ((∏ i ∈ Finset.Ioc (n / 2) n, ((2 : ℤ) ^ i - 1)) / ((2 : ℤ) ^ (k - j) - 1)), ?_⟩
  rw [Int.cast_sum, Finset.mul_sum]
  apply Finset.sum_congr rfl
  intro j hj
  rw [Finset.mem_range] at hj
  by_cases h0 : k - j = 0
  · simp [h0]
  · obtain ⟨q, hq⟩ := key (k - j) (by omega) (by omega)
    have hne : ((2 : ℤ) ^ (k - j) - 1) ≠ 0 := by
      have : (2 : ℤ) ^ 1 ≤ 2 ^ (k - j) := pow_le_pow_right₀ (by norm_num) (by omega)
      linarith
    have hneq : ((2 : ℚ) ^ (k - j) - 1) ≠ 0 := by
      have : (2 : ℚ) ^ 1 ≤ 2 ^ (k - j) := pow_le_pow_right₀ (by norm_num) (by omega)
      linarith
    have hP : (∏ i ∈ Finset.Ioc (n / 2) n, ((2 : ℚ) ^ i - 1)) = ((2 : ℚ) ^ (k - j) - 1) * (q : ℚ) := by
      have := congrArg (fun z : ℤ => (z : ℚ)) hq
      push_cast at this
      exact this
    rw [hq, Int.mul_ediv_cancel_left _ hne, hP]
    push_cast
    field_simp
