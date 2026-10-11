import Mathlib

open scoped ArithmeticFunction.omega
open Filter Topology

/-- erdos-69--h2-v2--h1-v2--h4 is no easier than the root erdos-69: the root implies it
(with N = 0 and k large), so the skeleton's crux restates the problem (D-12, D-16 v3.21). -/
theorem erdos_69_h4_circular :
    (Irrational <| ∑' n, ω (n + 2) / 2 ^ (n + 2)) →
    ∑' (n : ℕ), (↑((ω : ℕ → ℕ) n) : ℝ) / (2 : ℝ) ^ n = ∑' (p : Nat.Primes), (1 : ℝ) / ((2 : ℝ) ^ (↑p : ℕ) - (1 : ℝ)) →
  (∀ (N k : ℕ),
      ∑' (j : ℕ), (↑((ω : ℕ → ℕ) (N + (1 : ℕ) + j)) : ℝ) / (2 : ℝ) ^ (j + (1 : ℕ)) =
        ∑ j ∈ Finset.range k, (↑((ω : ℕ → ℕ) (N + (1 : ℕ) + j)) : ℝ) / (2 : ℝ) ^ (j + (1 : ℕ)) +
          (∑' (j : ℕ), (↑((ω : ℕ → ℕ) (N + k + (1 : ℕ) + j)) : ℝ) / (2 : ℝ) ^ (j + (1 : ℕ))) / (2 : ℝ) ^ k) →
    (∀ (M : ℕ), (0 : ℝ) < ∑' (j : ℕ), (↑((ω : ℕ → ℕ) (M + (1 : ℕ) + j)) : ℝ) / (2 : ℝ) ^ (j + (1 : ℕ))) →
      (∀ (M : ℕ),
          ∑' (j : ℕ), (↑((ω : ℕ → ℕ) (M + (1 : ℕ) + j)) : ℝ) / (2 : ℝ) ^ (j + (1 : ℕ)) ≤
            Real.logb (2 : ℝ) ((↑M : ℝ) + (1 : ℝ)) + (1 : ℝ)) →
        ∀ (b : ℕ),
          (0 : ℕ) < b →
            ∃ N k,
              (↑((b * ∑ j ∈ Finset.range k, (ω : ℕ → ℕ) (N + (1 : ℕ) + j) * (2 : ℕ) ^ (k - (1 : ℕ) - j)) %
                        (2 : ℕ) ^ k) :
                    ℝ) +
                  (↑b : ℝ) * (Real.logb (2 : ℝ) ((↑(N + k) : ℝ) + (1 : ℝ)) + (1 : ℝ)) <
                (2 : ℝ) ^ k := by
  intro hroot hL hsplit hpos hlog b hb
  have exists_k_small : ∀ c : ℝ, 0 < c → ∃ k : ℕ, (b : ℝ) * ((k : ℝ) + 1) < c * 2 ^ k := by
    intro c hc
    have h1 := tendsto_pow_const_div_const_pow_of_one_lt 1 (by norm_num : (1:ℝ) < 2)
    have h0 : Tendsto (fun n : ℕ => (1:ℝ) / 2 ^ n) atTop (𝓝 0) := by
      have := tendsto_pow_atTop_nhds_zero_of_lt_one (by norm_num : (0:ℝ) ≤ 1/2) (by norm_num : (1/2:ℝ) < 1)
      simpa [one_div, inv_pow] using this
    have hs := h1.add h0
    simp only [pow_one, add_zero] at hs
    have hpos : 0 < c / ((b:ℝ) + 1) := by positivity
    obtain ⟨k, hk⟩ := (hs.eventually (gt_mem_nhds hpos)).exists
    refine ⟨k, ?_⟩
    have h2k : (0:ℝ) < 2 ^ k := by positivity
    have : ((k:ℝ) + 1) / 2 ^ k < c / ((b:ℝ) + 1) := by
      rw [add_div]; exact hk
    rw [div_lt_div_iff₀ h2k (by positivity)] at this
    have hb0 : (0:ℝ) ≤ b := by positivity
    nlinarith [mul_nonneg hb0 (by positivity : (0:ℝ) ≤ (k:ℝ) + 1)]
  have hsum : Summable (fun j : ℕ => (↑((ω : ℕ → ℕ) (0 + (1 : ℕ) + j)) : ℝ) / (2 : ℝ) ^ (j + (1 : ℕ))) := by
    by_contra hns
    have := hpos 0
    rw [tsum_eq_zero_of_not_summable hns] at this
    exact lt_irrefl _ this
  have hS : ∑' (j : ℕ), (↑((ω : ℕ → ℕ) (0 + (1 : ℕ) + j)) : ℝ) / (2 : ℝ) ^ (j + (1 : ℕ)) =
      ∑' n : ℕ, (↑((ω : ℕ → ℕ) (n + 2)) : ℝ) / (2 : ℝ) ^ (n + 2) := by
    rw [hsum.tsum_eq_zero_add]
    rw [show (1 : ℕ) + 0 = 1 from rfl, ArithmeticFunction.cardDistinctFactors_one, Nat.cast_zero, zero_div,
      zero_add]
    refine tsum_congr (fun j => ?_)
    rw [show 1 + (j + 1) = j + 2 by omega, show j + 1 + 1 = j + 2 by omega]
  have hirr : ∀ z : ℤ, (b : ℝ) * ∑' (j : ℕ), (↑((ω : ℕ → ℕ) (0 + (1 : ℕ) + j)) : ℝ) / (2 : ℝ) ^ (j + (1 : ℕ)) ≠ z := by
    intro z
    rw [hS]
    exact (hroot.natCast_mul (Nat.pos_iff_ne_zero.mp hb)).ne_int z
  set T : ℕ → ℝ := fun M => ∑' (j : ℕ), (↑((ω : ℕ → ℕ) (M + (1 : ℕ) + j)) : ℝ) / (2 : ℝ) ^ (j + (1 : ℕ)) with hT
  set x : ℝ := (b : ℝ) * T 0 with hx
  set m : ℤ := ⌊x⌋ with hm
  set f : ℝ := x - m with hf
  have hf0 : 0 < f := by
    have h1 : (m : ℝ) ≤ x := Int.floor_le x
    have h2 : (m : ℝ) ≠ x := fun h => hirr m (by rw [← h])
    have := lt_of_le_of_ne h1 h2
    simp only [hf]; linarith
  have hf1 : f < 1 := by
    have := Int.lt_floor_add_one x
    simp only [hf]; linarith
  obtain ⟨k, hk⟩ := exists_k_small (min f (1 - f)) (lt_min hf0 (by linarith))
  refine ⟨0, k, ?_⟩
  -- the integer window
  set A : ℕ := ∑ j ∈ Finset.range k, (ω : ℕ → ℕ) (0 + (1 : ℕ) + j) * (2 : ℕ) ^ (k - (1 : ℕ) - j) with hA
  have hAreal : (A : ℝ) = 2 ^ k * ∑ j ∈ Finset.range k, (↑((ω : ℕ → ℕ) (0 + (1 : ℕ) + j)) : ℝ) / (2 : ℝ) ^ (j + (1 : ℕ)) := by
    simp only [hA, Nat.cast_sum, Nat.cast_mul, Nat.cast_pow, Nat.cast_ofNat, Finset.mul_sum]
    refine Finset.sum_congr rfl (fun j hj => ?_)
    have hj' : j < k := Finset.mem_range.mp hj
    have hpow : (2:ℝ) ^ k = 2 ^ (k - 1 - j) * 2 ^ (j + 1) := by
      rw [← pow_add]; congr 1; omega
    rw [hpow]; field_simp
  have hsp := hsplit 0 k
  have hg0 : 0 < (b:ℝ) * T k := by
    have := hpos k; simp only [hT]; positivity
  have hlogk : Real.logb 2 ((k:ℝ) + 1) ≤ k := by
    rw [Real.logb_le_iff_le_rpow (by norm_num) (by positivity)]
    rw [Real.rpow_natCast]
    exact_mod_cast Nat.lt_two_pow_self
  have hg1 : (b:ℝ) * T k ≤ b * ((k:ℝ) + 1) := by
    have := hlog k
    have hb0 : (0:ℝ) ≤ b := by positivity
    have : T k ≤ (k:ℝ) + 1 := by simp only [hT]; linarith
    exact mul_le_mul_of_nonneg_left this hb0
  -- b * A = 2^k * x - b * T k
  have hbA : ((b * A : ℕ) : ℝ) = 2 ^ k * x - b * T k := by
    push_cast
    rw [hAreal]
    have : T 0 = ∑ j ∈ Finset.range k, (↑((ω : ℕ → ℕ) (0 + (1 : ℕ) + j)) : ℝ) / (2 : ℝ) ^ (j + (1 : ℕ)) + T k / 2 ^ k := by
      simp only [hT]; simpa using hsp
    simp only [hx, this]
    field_simp
    ring
  set r : ℤ := ((b * A : ℕ) : ℤ) - 2 ^ k * m with hr
  have hrreal : (r : ℝ) = 2 ^ k * f - b * T k := by
    simp only [hr, hf]; push_cast
    rw [show ((b:ℝ) * (A:ℝ)) = ((b * A : ℕ) : ℝ) by push_cast; ring, hbA]; ring
  have h2k : (0:ℝ) < 2 ^ k := by positivity
  have hmin1 : min f (1 - f) ≤ f := min_le_left _ _
  have hmin2 : min f (1 - f) ≤ 1 - f := min_le_right _ _
  have hr0 : 0 ≤ r := by
    have : (0:ℝ) ≤ r := by
      rw [hrreal]; nlinarith
    exact_mod_cast this
  have hr1 : r < 2 ^ k := by
    have : (r:ℝ) < 2 ^ k := by rw [hrreal]; nlinarith
    exact_mod_cast this
  have hmod : (((b * A) % 2 ^ k : ℕ) : ℤ) = r := by
    push_cast
    have : ((b:ℤ) * (A:ℤ)) = r + 2 ^ k * m := by simp only [hr]; push_cast; ring
    rw [this, Int.add_mul_emod_self_left, Int.emod_eq_of_lt hr0 hr1]
  have hmodR : (((b * A) % 2 ^ k : ℕ) : ℝ) = 2 ^ k * f - b * T k := by
    rw [← hrreal, ← hmod]; push_cast; rfl
  rw [hmodR]
  have hl : Real.logb 2 (((0 + k : ℕ) : ℝ) + 1) ≤ k := by simpa using hlogk
  have hb0 : (0:ℝ) ≤ b := by positivity
  nlinarith [mul_le_mul_of_nonneg_left hl hb0]
