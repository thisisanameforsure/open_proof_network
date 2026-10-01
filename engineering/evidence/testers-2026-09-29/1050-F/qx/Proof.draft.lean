import Mathlib

/-- erdos-1050, hole hden (erdos-1050--h1-v2--h3), the Qx half of its integrality claim, from
annex 4670684d2f0d on that node: with `Qc` and `Qx` exactly as in h3, 2^(n(n+1)/2) * Qx n is an
integer. Each Qc n k is (-1)^k 2^(k(k-1)/2) times two Gaussian binomials at q = 2, integers by
spec-440db0f9 (the second is [2n-k, n]_2), so its term Qc n k (3/2^n)^k has 2-denominator at most
2^(nk - k(k-1)/2) ≤ 2^(n(n+1)/2), since n(n+1)/2 + k(k-1)/2 - nk = (n-k)(n-k+1)/2 ≥ 0. Hence
d = 2^(n(n+1)/2) times any odd factor clears Qx n; with spec-1a5ab7c3 this leaves only the
2-adic part of Aq n (the annex's v2(p_k(n)) ≥ k(k-1)/2) open for h3's integrality. -/
theorem erdos_1050_hden_Qx_two_power : ∀ (Qc : ℕ → ℕ → ℚ),
    (Qc = fun (n k : ℕ) =>
      ((-1 : ℚ) ^ k * (2 : ℚ) ^ (k * (k - 1) / 2) *
          ∏ i ∈ Finset.range k, ((2 : ℚ) ^ (n - i) - 1) / ((2 : ℚ) ^ (i + 1) - 1)) *
        ∏ i ∈ Finset.range n, ((2 : ℚ) ^ (2 * n - k - i) - 1) / ((2 : ℚ) ^ (i + 1) - 1)) →
    ∀ (Qx : ℕ → ℚ),
      (Qx = fun (n : ℕ) => ∑ k ∈ Finset.range (n + 1), Qc n k * ((3 : ℚ) / (2 : ℚ) ^ n) ^ k) →
        ∀ (n : ℕ), ∃ z : ℤ, (z : ℚ) = (2 : ℚ) ^ (n * (n + 1) / 2) * Qx n := by
  intro Qc hQc Qx hQx n
  subst hQc hQx
  choose g1 hg1 using fun k => erdos_1050_gauss_binom_two_int n k
  choose g2 hg2 using fun k => erdos_1050_gauss_binom_two_int (2 * n - k) n
  refine ⟨∑ k ∈ Finset.range (n + 1),
      (-1) ^ k * g1 k * g2 k * 3 ^ k * 2 ^ (n * (n + 1) / 2 + k * (k - 1) / 2 - n * k), ?_⟩
  push_cast
  rw [Finset.mul_sum]
  apply Finset.sum_congr rfl
  intro k hk
  rw [Finset.mem_range] at hk
  have hkn : k ≤ n := by omega
  have hA : n * (n + 1) / 2 * 2 = n * (n + 1) :=
    Nat.div_mul_cancel (Nat.even_mul_succ_self n).two_dvd
  have hB : k * (k - 1) / 2 * 2 = k * (k - 1) :=
    Nat.div_mul_cancel (Nat.even_mul_pred_self k).two_dvd
  have he : n * k ≤ n * (n + 1) / 2 + k * (k - 1) / 2 := by
    obtain ⟨d, rfl⟩ : ∃ d, n = k + d := ⟨n - k, by omega⟩
    rcases k with _ | j
    · simp
    · have hB' : (j + 1) * (j + 1 - 1) = (j + 1) * j := by simp
      rw [hB'] at hB ⊢
      nlinarith [hA, hB, Nat.zero_le (d * d)]
  obtain ⟨e, he'⟩ : ∃ e, n * (n + 1) / 2 + k * (k - 1) / 2 = e + n * k :=
    ⟨_, (Nat.sub_add_cancel he).symm⟩
  have hsub : n * (n + 1) / 2 + k * (k - 1) / 2 - n * k = e := by omega
  rw [hsub, ← hg1 k, ← hg2 k]
  have h2 : (2 : ℚ) ^ (n * (n + 1) / 2) * 2 ^ (k * (k - 1) / 2) = 2 ^ e * ((2 : ℚ) ^ n) ^ k := by
    rw [← pow_mul, ← pow_add, ← pow_add, he', mul_comm n k]
  rw [div_pow]
  have h2n : ((2 : ℚ) ^ n) ^ k ≠ 0 := by positivity
  field_simp
  linear_combination (-(g1 k : ℚ) * (g2 k : ℚ)) * h2
