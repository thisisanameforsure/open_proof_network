import Mathlib

/-- The binary-weighted density of the integers `m + k + 1` (k ≥ 0) divisible by `p`. -/
theorem indicator_tsum (p m : ℕ) (hp : 0 < p) :
    ∑' k : ℕ, (if p ∣ m + (k + 1) then (1 : ℝ) else 0) / 2 ^ (k + 1)
      = (2 : ℝ) ^ (m % p) / (2 ^ p - 1) := by
  set g : ℕ → ℝ := fun k => (if p ∣ m + (k + 1) then (1 : ℝ) else 0) / 2 ^ (k + 1) with hg
  have hgeo : Summable (fun k : ℕ => (1 : ℝ) / 2 ^ (k + 1)) := by
    refine (summable_geometric_two.mul_left (1 / 2 : ℝ)).congr (fun k => ?_)
    rw [one_div, one_div, ← inv_pow, pow_succ, mul_comm]
  have hs : Summable g := by
    refine Summable.of_nonneg_of_le (fun k => ?_) (fun k => ?_) hgeo
    · simp only [hg]; split_ifs <;> positivity
    · simp only [hg]; split_ifs
      · exact le_rfl
      · rw [zero_div]; positivity
  have hmod : ∀ i : ℕ, p ∣ m + (i + 1) ↔ p ∣ m % p + (i + 1) := by
    intro i
    conv_lhs => rw [← Nat.div_add_mod m p, add_assoc]
    exact Nat.dvd_add_right (dvd_mul_right _ _)
  have hr : m % p < p := Nat.mod_lt _ hp
  set r := m % p with hrdef
  set k0 := p - 1 - r with hk0
  have hk0p : k0 < p := by omega
  have hsum_p : k0 + 1 + r = p := by omega
  -- the periodic step
  have hper : ∀ i : ℕ, g (i + p) = g i / 2 ^ p := by
    intro i
    simp only [hg]
    have : p ∣ m + (i + p + 1) ↔ p ∣ m + (i + 1) := by
      rw [show m + (i + p + 1) = m + (i + 1) + p by ring]
      exact Nat.dvd_add_self_right
    rw [if_congr this rfl rfl, show i + p + 1 = (i + 1) + p by ring, pow_add, div_div]
  -- the first period contributes exactly one term, at k0
  have hfin : ∑ i ∈ Finset.range p, g i = 1 / 2 ^ (k0 + 1) := by
    rw [Finset.sum_eq_single k0]
    · simp only [hg]
      rw [if_pos]
      rw [hmod, show r + (k0 + 1) = p by omega]
    · intro i hi hne
      simp only [hg]
      rw [if_neg, zero_div]
      rw [hmod]
      intro hd
      have hi' : i < p := Finset.mem_range.mp hi
      have hpos : r + (i + 1) ≠ 0 := by omega
      have hlt : r + (i + 1) < 2 * p := by omega
      have := Nat.eq_of_dvd_of_lt_two_mul hpos hd hlt
      omega
    · intro h; exact absurd (Finset.mem_range.mpr hk0p) h
  have h := hs.sum_add_tsum_nat_add p
  rw [tsum_congr hper, tsum_div_const, hfin] at h
  have h2p : (2 : ℝ) ^ p = 2 ^ (k0 + 1) * 2 ^ r := by rw [← pow_add, hsum_p]
  have hne : (2 : ℝ) ^ p - 1 ≠ 0 := by
    have : (1 : ℝ) < 2 ^ p := one_lt_pow₀ (by norm_num) hp.ne'
    linarith
  have hpow : (0 : ℝ) < 2 ^ p := by positivity
  have hpow1 : (0 : ℝ) < 2 ^ (k0 + 1) := by positivity
  -- solve S = 1/2^(k0+1) + S/2^p for S
  rw [eq_div_iff hne, h2p]
  rw [h2p] at h
  field_simp at h
  linear_combination -h
