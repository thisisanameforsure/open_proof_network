import Mathlib

open scoped Nat

theorem h_gr_test : ∀ C : ℕ, ∃ K₂ : ℕ, ∀ n k : ℕ, K₂ < k → k * k ≤ C * (n * Nat.log 2 k) →
      n < k * k → ∃ p : ℕ, p.Prime ∧ k < 2 * p ∧ 20 * p < 11 * k ∧ n % p < k % p := by
  have h_cheb : ∃ c : ℝ, 0 < c ∧ ∃ K₃ : ℕ, ∀ k : ℕ, K₃ < k →
      c * (k : ℝ) ≤ ∑ p ∈ (Finset.range k).filter (fun p => p.Prime ∧ k < 2 * p ∧ 20 * p < 11 * k),
        Real.log (p : ℝ) := by
    sorry
  have h_sander : ∀ C : ℕ, ∀ ε : ℝ, 0 < ε → ∃ K₄ : ℕ, ∀ n k : ℕ, K₄ < k →
      k * k ≤ C * (n * Nat.log 2 k) → n < k * k →
      |∑ p ∈ (Finset.range k).filter (fun p => p.Prime ∧ k < 2 * p ∧ 20 * p < 11 * k),
        (Int.fract (((n - k : ℕ) : ℝ) / (p : ℝ)) - 1 / 2) * Real.log (p : ℝ)| ≤ ε * (k : ℝ) := by
    sorry
  intro C
  obtain ⟨c, hc, K₃, hK₃⟩ := h_cheb
  obtain ⟨K₄, hK₄⟩ := h_sander C (3 * c / 20) (by positivity)
  refine ⟨max K₃ K₄, fun n k hK hkk hn => ?_⟩
  have h3 : K₃ < k := lt_of_le_of_lt (le_max_left _ _) hK
  have h4 : K₄ < k := lt_of_le_of_lt (le_max_right _ _) hK
  by_contra hno
  push_neg at hno
  set S := (Finset.range k).filter (fun p => p.Prime ∧ k < 2 * p ∧ 20 * p < 11 * k) with hS
  have hterm : ∀ p ∈ S, (Int.fract (((n - k : ℕ) : ℝ) / (p : ℝ)) - 1 / 2) * Real.log (p : ℝ)
      ≤ -(3 / 10) * Real.log (p : ℝ) := by
    intro p hp
    rw [hS, Finset.mem_filter, Finset.mem_range] at hp
    obtain ⟨hpk, hpp, h2p, h20⟩ := hp
    have hp0 : 0 < p := hpp.pos
    have hnc := hno p hpp h2p h20
    have hkp : k % p = k - p := by
      rw [Nat.mod_eq_sub_mod (by omega), Nat.mod_eq_of_lt (by omega)]
    have hr : 5 * ((n - k) % p) < p := by
      rcases Nat.lt_or_ge n k with hnk | hnk
      · rw [Nat.sub_eq_zero_of_le hnk.le, Nat.zero_mod]; omega
      · have hsplit : n % p = ((n - k) % p + k % p) % p := by
          rw [← Nat.add_mod, Nat.sub_add_cancel hnk]
        have hrp : (n - k) % p < p := Nat.mod_lt _ hp0
        rw [hkp] at hsplit hnc
        rcases Nat.lt_or_ge ((n - k) % p + (k - p)) p with hlt | hge
        · omega
        · rw [Nat.mod_eq_sub_mod hge,
            Nat.mod_eq_of_lt (show (n - k) % p + (k - p) - p < p by omega)] at hsplit
          omega
    have hfr : Int.fract (((n - k : ℕ) : ℝ) / (p : ℝ)) = (((n - k) % p : ℕ) : ℝ) / (p : ℝ) :=
      Int.fract_div_natCast_eq_div_natCast_mod
    have hpR : (0 : ℝ) < p := by exact_mod_cast hp0
    have hlt : (((n - k) % p : ℕ) : ℝ) / (p : ℝ) < 1 / 5 := by
      rw [div_lt_iff₀ hpR]
      have : ((5 * ((n - k) % p) : ℕ) : ℝ) < (p : ℝ) := by exact_mod_cast hr
      push_cast at this
      linarith
    have hlog : 0 ≤ Real.log (p : ℝ) := Real.log_nonneg (by exact_mod_cast hp0)
    rw [hfr]
    nlinarith
  have hsum : ∑ p ∈ S, (Int.fract (((n - k : ℕ) : ℝ) / (p : ℝ)) - 1 / 2) * Real.log (p : ℝ)
      ≤ -(3 / 10) * ∑ p ∈ S, Real.log (p : ℝ) := by
    rw [Finset.mul_sum]
    exact Finset.sum_le_sum hterm
  have hc3 := hK₃ k h3
  have hs4 := hK₄ n k h4 hkk hn
  rw [← hS] at hc3 hs4
  have hkpos : (0 : ℝ) < k := by exact_mod_cast (show 0 < k by omega)
  have habs := neg_abs_le (∑ p ∈ S, (Int.fract (((n - k : ℕ) : ℝ) / (p : ℝ)) - 1 / 2) * Real.log (p : ℝ))
  nlinarith
