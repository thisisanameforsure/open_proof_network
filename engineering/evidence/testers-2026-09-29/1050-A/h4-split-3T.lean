import Mathlib

theorem split3T (n : ℕ) :
    3 * ∑' m : ℕ, (1 : ℝ) / (2 ^ (m + 3) - 3) =
      ∑ j ∈ Finset.range n, (3 : ℝ) / (2 ^ (j + 1) - 3) + ∑' m : ℕ, (3 : ℝ) / (2 ^ (m + n + 1) - 3) := by
  set g : ℕ → ℝ := fun m => (3 : ℝ) / (2 ^ (m + 1) - 3) with hg
  have hsum : Summable (fun m => g (m + 1)) := by
    refine Summable.of_nonneg_of_le (fun m => ?_) (fun m => ?_) ((summable_geometric_two).mul_left 3)
    · have : (4 : ℝ) ≤ 2 ^ (m + 1 + 1) := by
        calc (4 : ℝ) = 2 ^ 2 := by norm_num
          _ ≤ 2 ^ (m + 1 + 1) := pow_le_pow_right₀ (by norm_num) (by omega)
      simp only [hg]; exact div_nonneg (by norm_num) (by linarith)
    · have hpow : (2 : ℝ) ^ (m + 2) ≤ 2 ^ (m + 1 + 1) := le_of_eq (by ring_nf)
      have h1 : (1 : ℝ) ≤ 2 ^ m := one_le_pow₀ (by norm_num)
      have h2 : (2 : ℝ) ^ (m + 2) = 4 * 2 ^ m := by rw [pow_add]; ring
      simp only [hg]
      calc (3 : ℝ) / (2 ^ (m + 1 + 1) - 3) ≤ 3 / 2 ^ m :=
            div_le_div_of_nonneg_left (by norm_num) (by positivity) (by linarith)
        _ = 3 * (1 / 2) ^ m := by rw [one_div_pow]; ring
  have hs : Summable g := (summable_nat_add_iff 1).mp hsum
  have e1 := hs.sum_add_tsum_nat_add n
  have e2 := hs.sum_add_tsum_nat_add 2
  have h3T : 3 * ∑' m : ℕ, (1 : ℝ) / (2 ^ (m + 3) - 3) = ∑' m, g (m + 2) := by
    rw [← tsum_mul_left]
    refine tsum_congr (fun m => ?_)
    simp only [hg]
    rw [show m + 2 + 1 = m + 3 by ring]
    ring
  have hfirst : ∑ i ∈ Finset.range 2, g i = 0 := by
    simp only [hg, Finset.sum_range_succ, Finset.sum_range_zero]
    norm_num
  rw [h3T]
  have htail : ∑' m : ℕ, (3 : ℝ) / (2 ^ (m + n + 1) - 3) = ∑' m, g (m + n) := by
    refine tsum_congr (fun m => ?_)
    simp only [hg]
  rw [htail]
  have hrange : ∑ j ∈ Finset.range n, (3 : ℝ) / (2 ^ (j + 1) - 3) = ∑ i ∈ Finset.range n, g i := by
    simp only [hg]
  rw [hrange, e1]
  rw [← e2, hfirst, zero_add]
