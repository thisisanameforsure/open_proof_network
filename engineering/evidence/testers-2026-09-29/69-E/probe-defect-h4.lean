import Mathlib

open scoped ArithmeticFunction.omega

/-- erdos-69--h2-v2--h1-v2--h4 is no easier than erdos-69--h2-v2: composing the two merged
circularity exhibits h2-v2 → h2-v2--h1-v2 and h2-v2--h1-v2 → h4 (both by t0924-69m-8709). -/
theorem erdos_69_h4_from_h2_v2 :
    ((∑' n : ℕ, (ω n : ℝ) / 2 ^ n
      = ∑' p : Nat.Primes, (1 : ℝ) / (2 ^ (p : ℕ) - 1)) →
    Irrational (∑' p : Nat.Primes, (1 : ℝ) / (2 ^ (p : ℕ) - 1))) →
    (∑' (n : ℕ), (↑((ω : ℕ → ℕ) n) : ℝ) / (2 : ℝ) ^ n = ∑' (p : Nat.Primes), (1 : ℝ) / ((2 : ℝ) ^ (↑p : ℕ) - (1 : ℝ)) →
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
                (2 : ℝ) ^ k) := by
  have hA : ((∑' n : ℕ, (ω n : ℝ) / 2 ^ n
      = ∑' p : Nat.Primes, (1 : ℝ) / (2 ^ (p : ℕ) - 1)) →
    Irrational (∑' p : Nat.Primes, (1 : ℝ) / (2 ^ (p : ℕ) - 1))) →
    ((∑' n : ℕ, (ω n : ℝ) / 2 ^ n = ∑' p : Nat.Primes, (1 : ℝ) / (2 ^ (p : ℕ) - 1)) →
    ∀ b : ℕ, 0 < b → ∃ N : ℕ, ∀ z : ℤ,
      (b : ℝ) * ∑' j : ℕ, (ω (N + 1 + j) : ℝ) / 2 ^ (j + 1) ≠ (z : ℝ)) := by
      intro hanc hL b hb
      have hsum : Summable (fun n : ℕ => (ω n : ℝ) / 2 ^ n) := by
        have hbound : ∀ n : ℕ,
            (ω n : ℝ) / 2 ^ n ≤ (n : ℝ) ^ 1 * (1 / 2 : ℝ) ^ n + (1 / 2 : ℝ) ^ n := by
          intro n
          have h1 : ω n ≤ n + 1 := by
            rw [ArithmeticFunction.cardDistinctFactors_apply]
            calc n.primeFactorsList.dedup.length = n.primeFactors.card := rfl
              _ ≤ (Finset.range (n + 1)).card :=
                  Finset.card_le_card (fun p hp =>
                    Finset.mem_range.2 (Nat.lt_succ_of_le (Nat.le_of_mem_primeFactors hp)))
              _ = n + 1 := Finset.card_range _
          have h2 : (ω n : ℝ) ≤ (n : ℝ) + 1 := by exact_mod_cast h1
          have h4 : (0 : ℝ) ≤ ((2 : ℝ) ^ n)⁻¹ := by positivity
          rw [pow_one, one_div, inv_pow, div_eq_mul_inv]
          nlinarith [mul_le_mul_of_nonneg_right h2 h4]
        refine Summable.of_nonneg_of_le (fun n => by positivity) hbound ?_
        exact (summable_pow_mul_geometric_of_norm_lt_one 1 (by norm_num [Real.norm_eq_abs])).add
          (summable_geometric_of_lt_one (by norm_num) (by norm_num))
      have tail_zero :
          ∑' j : ℕ, (ω (0 + 1 + j) : ℝ) / 2 ^ (j + 1) = ∑' n : ℕ, (ω n : ℝ) / 2 ^ n := by
        have h1 : ∑' n : ℕ, (ω n : ℝ) / 2 ^ n = ∑' n : ℕ, (ω (n + 1) : ℝ) / 2 ^ (n + 1) := by
          rw [hsum.tsum_eq_zero_add]
          simp
        rw [h1]
        refine tsum_congr (fun j => ?_)
        rw [show 0 + 1 + j = j + 1 by omega]
      have hirr : Irrational (∑' n : ℕ, (ω n : ℝ) / 2 ^ n) := by
        rw [hL]; exact hanc hL
      refine ⟨0, fun z hz => ?_⟩
      rw [tail_zero] at hz
      exact (hirr.natCast_mul hb.ne').ne_int z hz
  have hB : ((∑' n : ℕ, (ω n : ℝ) / 2 ^ n = ∑' p : Nat.Primes, (1 : ℝ) / (2 ^ (p : ℕ) - 1)) →
    ∀ b : ℕ, 0 < b → ∃ N : ℕ, ∀ z : ℤ,
      (b : ℝ) * ∑' j : ℕ, (ω (N + 1 + j) : ℝ) / 2 ^ (j + 1) ≠ (z : ℝ)) →
    (∑' (n : ℕ), (↑((ω : ℕ → ℕ) n) : ℝ) / (2 : ℝ) ^ n = ∑' (p : Nat.Primes), (1 : ℝ) / ((2 : ℝ) ^ (↑p : ℕ) - (1 : ℝ)) →
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
                (2 : ℝ) ^ k) := by
      intro hanc hL hsplit hpos hbound b hb
      obtain ⟨N, hN⟩ := hanc hL b hb
      have hb' : (0 : ℝ) < b := by exact_mod_cast hb
      -- t = b * T N is positive and not an integer
      set t : ℝ := (b : ℝ) * ∑' j : ℕ, (ω (N + 1 + j) : ℝ) / 2 ^ (j + 1) with ht
      have ht0 : 0 < t := mul_pos hb' (hpos N)
      set m : ℕ := ⌊t⌋₊ with hm
      have hm1 : (m : ℝ) ≤ t := Nat.floor_le ht0.le
      have hm2 : t < (m : ℝ) + 1 := Nat.lt_floor_add_one t
      have hne : (m : ℝ) ≠ t := by
        intro h
        exact hN (m : ℤ) (by rw [Int.cast_natCast]; exact h.symm)
      have hlt : (m : ℝ) < t := lt_of_le_of_ne hm1 hne
      set c : ℝ := min (t - m) ((m : ℝ) + 1 - t) with hc
      have hc0 : 0 < c := lt_min (by linarith) (by linarith)
      have hc1 : c ≤ t - m := min_le_left _ _
      have hc2 : c ≤ (m : ℝ) + 1 - t := min_le_right _ _
      -- choose k = n + n with 2^n large
      obtain ⟨n, hn⟩ := pow_unbounded_of_one_lt (2 * b * ((N : ℝ) + 2) / c) (by norm_num : (1 : ℝ) < 2)
      refine ⟨N, n + n, ?_⟩
      set k := n + n with hk
      have h2n : (0 : ℝ) < 2 ^ n := by positivity
      have hn1 : ((n : ℝ) + 1) ≤ 2 ^ n := by
        have : n + 1 ≤ 2 ^ n := Nat.lt_two_pow_self
        exact_mod_cast this
      have hcn : 2 * b * ((N : ℝ) + 2) < c * 2 ^ n := by
        rw [div_lt_iff₀ hc0] at hn
        linarith
      have hlog : Real.logb 2 (((N + k : ℕ) : ℝ) + 1) ≤ ((N + k : ℕ) : ℝ) := by
        have hj : (0 : ℝ) < ((N + k : ℕ) : ℝ) + 1 := by positivity
        rw [Real.logb_le_iff_le_rpow (by norm_num) hj, Real.rpow_natCast]
        have : N + k + 1 ≤ 2 ^ (N + k) := Nat.lt_two_pow_self
        exact_mod_cast this
      have h2k : (2 : ℝ) ^ k = 2 ^ n * 2 ^ n := by rw [hk, pow_add]
      have hkey : (b : ℝ) * (Real.logb 2 (((N + k : ℕ) : ℝ) + 1) + 1) < c * 2 ^ k := by
        have e1 : (b : ℝ) * (Real.logb 2 (((N + k : ℕ) : ℝ) + 1) + 1) ≤ b * ((N : ℝ) + 2 * n + 1) := by
          apply mul_le_mul_of_nonneg_left _ hb'.le
          have hk' : (k : ℝ) = 2 * n := by rw [hk]; push_cast; ring
          push_cast at hlog ⊢
          linarith
        have e2 : (b : ℝ) * ((N : ℝ) + 2 * n + 1) ≤ 2 * b * ((N : ℝ) + 2) * ((n : ℝ) + 1) := by
          have h0 : (0 : ℝ) ≤ N := Nat.cast_nonneg N
          have h1 : (0 : ℝ) ≤ n := Nat.cast_nonneg n
          nlinarith [mul_nonneg hb'.le (mul_nonneg h0 h1), mul_nonneg hb'.le h0, mul_nonneg hb'.le h1]
        have e3 : 2 * b * ((N : ℝ) + 2) * ((n : ℝ) + 1) < c * 2 ^ n * 2 ^ n := by
          have : (0 : ℝ) < (n : ℝ) + 1 := by positivity
          calc 2 * b * ((N : ℝ) + 2) * ((n : ℝ) + 1) < c * 2 ^ n * ((n : ℝ) + 1) :=
                mul_lt_mul_of_pos_right hcn this
            _ ≤ c * 2 ^ n * 2 ^ n := mul_le_mul_of_nonneg_left hn1 (by positivity)
        rw [h2k]; linarith
      -- the finite sum A as 2^k times the partial sum
      have hA : ((∑ j ∈ Finset.range k, ω (N + 1 + j) * 2 ^ (k - 1 - j) : ℕ) : ℝ)
          = 2 ^ k * ∑ j ∈ Finset.range k, (ω (N + 1 + j) : ℝ) / 2 ^ (j + 1) := by
        push_cast
        rw [Finset.mul_sum]
        apply Finset.sum_congr rfl
        intro j hj
        rw [Finset.mem_range] at hj
        have : (2 : ℝ) ^ k = 2 ^ (k - 1 - j) * 2 ^ (j + 1) := by
          rw [← pow_add]; congr 1; omega
        rw [this]
        field_simp
      set A : ℕ := ∑ j ∈ Finset.range k, ω (N + 1 + j) * 2 ^ (k - 1 - j) with hAdef
      set δ : ℝ := (b : ℝ) * ∑' j : ℕ, (ω (N + k + 1 + j) : ℝ) / 2 ^ (j + 1) with hδ
      have hδ0 : 0 < δ := mul_pos hb' (by simpa [add_assoc] using hpos (N + k))
      have hδ1 : δ ≤ (b : ℝ) * (Real.logb 2 (((N + k : ℕ) : ℝ) + 1) + 1) := by
        apply mul_le_mul_of_nonneg_left _ hb'.le
        have := hbound (N + k)
        push_cast at this ⊢
        exact this
      have hsp := hsplit N k
      have hpk : (0 : ℝ) < 2 ^ k := by positivity
      have hBA : ((b * A : ℕ) : ℝ) = 2 ^ k * t - δ := by
        push_cast
        rw [hA, ht, hδ, hsp]
        field_simp
        ring
      -- so 2^k m < b A < 2^k (m+1)
      have hlo : ((2 ^ k * m : ℕ) : ℝ) < ((b * A : ℕ) : ℝ) := by
        rw [hBA]; push_cast
        nlinarith
      have hhi : ((b * A : ℕ) : ℝ) < (((m + 1) * 2 ^ k : ℕ) : ℝ) := by
        rw [hBA]; push_cast
        nlinarith
      have hdiv : (b * A) / 2 ^ k = m :=
        Nat.div_eq_of_lt_le (by rw [mul_comm]; exact_mod_cast hlo.le) (by exact_mod_cast hhi)
      have hmod : (((b * A) % 2 ^ k : ℕ) : ℝ) = ((b * A : ℕ) : ℝ) - 2 ^ k * m := by
        have h := Nat.mod_add_div (b * A) (2 ^ k)
        rw [hdiv] at h
        have h' : (((b * A) % 2 ^ k : ℕ) : ℝ) + ((2 ^ k * m : ℕ) : ℝ) = ((b * A : ℕ) : ℝ) := by
          exact_mod_cast h
        push_cast at h' ⊢
        linarith
      show (((b * A) % 2 ^ k : ℕ) : ℝ) + (b : ℝ) * (Real.logb 2 (((N + k : ℕ) : ℝ) + 1) + 1) < 2 ^ k
      rw [hmod, hBA]
      nlinarith
  exact fun h => hB (hA h)
