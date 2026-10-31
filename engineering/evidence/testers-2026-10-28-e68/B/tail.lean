import Mathlib

/-- K!·(K+1)^(j+1) ≤ (K+1+j)!, as reals. -/
private theorem B_fact_ge (K j : ℕ) :
    ((K.factorial : ℝ) * ((K : ℝ) + 1) ^ (j + 1)) ≤ ((j + K + 1).factorial : ℝ) := by
  have h := Nat.factorial_mul_pow_le_factorial (m := K) (n := j + 1)
  have he : K + (j + 1) = j + K + 1 := by omega
  rw [he] at h
  exact_mod_cast h

/-- one tail term, scaled by K!, is at most (1/K)·(1/(K+1))^j. -/
private theorem B_tail_term (K j : ℕ) (hK : 1 ≤ K) :
    (K.factorial : ℝ) * (1 / (((j + K + 1).factorial : ℝ) - 1)) ≤
      (1 / (K : ℝ)) * (1 / ((K : ℝ) + 1)) ^ j := by
  have hKr : (1:ℝ) ≤ K := by exact_mod_cast hK
  have hf := B_fact_ge K j
  have hKf : (1:ℝ) ≤ (K.factorial : ℝ) := by exact_mod_cast Nat.one_le_iff_ne_zero.mpr (Nat.factorial_ne_zero K)
  have hp : (K + 1 : ℝ) ≤ ((K : ℝ) + 1) ^ (j + 1) := by
    calc (K + 1 : ℝ) = ((K:ℝ) + 1) ^ 1 := by ring
      _ ≤ ((K : ℝ) + 1) ^ (j + 1) := pow_le_pow_right₀ (by linarith) (by omega)
  -- m! - 1 ≥ m! * K/(K+1) since m! ≥ K+1
  have hm1 : ((K : ℝ) + 1) ≤ ((j + K + 1).factorial : ℝ) := by nlinarith
  have hden : 0 < ((j + K + 1).factorial : ℝ) - 1 := by linarith
  have hpow : 0 < ((K : ℝ) + 1) ^ j := by positivity
  rw [div_pow, one_pow, mul_one_div, one_div_mul_one_div, div_le_div_iff₀ hden (by positivity)]
  -- K! * (K * (K+1)^j) ≤ m! - 1
  have : (K.factorial : ℝ) * ((K : ℝ) * ((K : ℝ) + 1) ^ j) * ((K:ℝ) + 1) ≤
      (((j + K + 1).factorial : ℝ) - 1) * ((K:ℝ) + 1) := by
    have e : (K.factorial : ℝ) * ((K : ℝ) * ((K : ℝ) + 1) ^ j) * ((K:ℝ) + 1)
        = (K : ℝ) * ((K.factorial : ℝ) * ((K : ℝ) + 1) ^ (j + 1)) := by ring
    rw [e]
    nlinarith
  nlinarith

/-- The scaled tail K!·Σ_{m ≥ K+1} 1/(m!−1) lies in (0, (K+1)/K²]. -/
private theorem B_tail_bound (K : ℕ) (hK : 1 ≤ K) :
    0 < (K.factorial : ℝ) * ∑' j : ℕ, 1 / (((j + K + 1).factorial : ℝ) - 1) ∧
      (K.factorial : ℝ) * ∑' j : ℕ, 1 / (((j + K + 1).factorial : ℝ) - 1) ≤
        ((K : ℝ) + 1) / (K : ℝ) ^ 2 := by
  have hKr : (1:ℝ) ≤ K := by exact_mod_cast hK
  have hpos : ∀ j : ℕ, 0 < ((j + K + 1).factorial : ℝ) - 1 := by
    intro j
    have : (2:ℕ) ≤ (j + K + 1).factorial := by
      have := Nat.factorial_le (show 2 ≤ j + K + 1 by omega)
      simpa using this
    have : (2:ℝ) ≤ ((j + K + 1).factorial : ℝ) := by exact_mod_cast this
    linarith
  have hKf : (0:ℝ) < (K.factorial : ℝ) := by exact_mod_cast Nat.factorial_pos K
  have hr : 1 / ((K : ℝ) + 1) < 1 := by
    rw [div_lt_one (by linarith)]; linarith
  have hgeo : Summable (fun j : ℕ => (1 / (K : ℝ)) * (1 / ((K : ℝ) + 1)) ^ j) :=
    (summable_geometric_of_lt_one (by positivity) hr).mul_left _
  have hle : ∀ j : ℕ, 1 / (((j + K + 1).factorial : ℝ) - 1) ≤
      (1 / (K.factorial : ℝ)) * ((1 / (K : ℝ)) * (1 / ((K : ℝ) + 1)) ^ j) := by
    intro j
    have := B_tail_term K j hK
    calc 1 / (((j + K + 1).factorial : ℝ) - 1)
        = (1 / (K.factorial : ℝ)) * ((K.factorial : ℝ) * (1 / (((j + K + 1).factorial : ℝ) - 1))) := by
          field_simp
      _ ≤ (1 / (K.factorial : ℝ)) * ((1 / (K : ℝ)) * (1 / ((K : ℝ) + 1)) ^ j) := by
          gcongr
  have hs : Summable (fun j : ℕ => 1 / (((j + K + 1).factorial : ℝ) - 1)) :=
    Summable.of_nonneg_of_le (fun j => (one_div_pos.mpr (hpos j)).le) hle (hgeo.mul_left _)
  constructor
  · apply mul_pos hKf
    exact hs.tsum_pos (fun j => (one_div_pos.mpr (hpos j)).le) 0 (one_div_pos.mpr (hpos 0))
  · have h1 := hs.tsum_le_tsum hle (hgeo.mul_left _)
    rw [tsum_mul_left, tsum_mul_left, tsum_geometric_of_lt_one (by positivity) hr] at h1
    have hK0 : (K : ℝ) ≠ 0 := by linarith
    have hK1 : (K : ℝ) + 1 ≠ 0 := by linarith
    have hgs : (1 - 1 / ((K : ℝ) + 1))⁻¹ = ((K : ℝ) + 1) / K := by
      rw [one_sub_div hK1, inv_div]; ring
    rw [hgs] at h1
    calc (K.factorial : ℝ) * ∑' j : ℕ, 1 / (((j + K + 1).factorial : ℝ) - 1)
        ≤ (K.factorial : ℝ) * ((1 / (K.factorial : ℝ)) * ((1 / (K : ℝ)) * (((K : ℝ) + 1) / K))) := by
          gcongr
      _ = ((K : ℝ) + 1) / (K : ℝ) ^ 2 := by field_simp

/-- C's h_tail shape. -/
theorem C_h_tail : ∀ N : ℕ, 1 ≤ N →
      0 < ((N + 2).factorial : ℝ) * ∑' i : ℕ, 1 / ((i + (N + 1) + 2).factorial - 1 : ℝ) ∧
      ((N + 2).factorial : ℝ) * ∑' i : ℕ, 1 / ((i + (N + 1) + 2).factorial - 1 : ℝ) < 1 / 2 := by
  intro N hN
  have he : ∀ i : ℕ, i + (N + 1) + 2 = i + (N + 2) + 1 := fun i => by omega
  simp only [he]
  obtain ⟨h0, h1⟩ := B_tail_bound (N + 2) (by omega)
  refine ⟨h0, lt_of_le_of_lt h1 ?_⟩
  have hN' : (1:ℝ) ≤ N := by exact_mod_cast hN
  push_cast
  rw [div_lt_iff₀ (by positivity)]
  nlinarith
