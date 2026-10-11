import Mathlib

open scoped ArithmeticFunction.omega

theorem Opn.erdos_69_dilated_tail_closed :
    ∀ (a m : ℕ), a ≠ 0 →
      ∑' k : ℕ, (ω (a * (m + (k + 1))) : ℝ) / 2 ^ (k + 1)
        = ∑' k : ℕ, (ω (m + (k + 1)) : ℝ) / 2 ^ (k + 1) + (ω a : ℝ)
          - ∑ p ∈ a.primeFactors, (2 : ℝ) ^ (m % p) / (2 ^ p - 1) := by
  intro a m ha
  -- (i) the density of the multiples of p among m + 1, m + 2, … in binary weights
  have hcl : ∀ (p m : ℕ), 0 < p →
      ∑' k : ℕ, (if p ∣ m + (k + 1) then (1 : ℝ) else 0) / 2 ^ (k + 1)
        = 2 ^ (m % p) / (2 ^ p - 1) := by
    intro p m hp
    obtain ⟨s, hs⟩ : ∃ s, s = m % p := ⟨_, rfl⟩
    obtain ⟨Q, hQ⟩ : ∃ Q, Q = m / p := ⟨_, rfl⟩
    have hsp : s < p := hs ▸ Nat.mod_lt _ hp
    have hm : m = s + p * Q := by rw [hs, hQ]; exact (Nat.mod_add_div m p).symm
    rw [← hs]
    obtain ⟨k0, hk0⟩ : ∃ k0, k0 = p - 1 - s := ⟨_, rfl⟩
    have hdiv : ∀ k : ℕ, p ∣ m + (k + 1) ↔ ∃ t, k0 + p * t = k := by
      intro k
      constructor
      · rintro ⟨c, hc⟩
        have hcQ : Q < c := by
          have : p * Q < p * c := by omega
          exact Nat.lt_of_mul_lt_mul_left this
        obtain ⟨e, he⟩ : ∃ e, c = Q + 1 + e := ⟨c - Q - 1, by omega⟩
        refine ⟨e, ?_⟩
        rw [he, mul_add, mul_add, mul_one] at hc
        omega
      · rintro ⟨t, rfl⟩
        exact ⟨Q + 1 + t, by rw [mul_add, mul_add, mul_one]; omega⟩
    let f : ℕ → ℝ := fun k => (if p ∣ m + (k + 1) then (1 : ℝ) else 0) / 2 ^ (k + 1)
    let g : ℕ → ℕ := fun t => k0 + p * t
    have hg : Function.Injective g := by
      intro t t' h
      have : p * t = p * t' := by simp only [g] at h; omega
      exact Nat.eq_of_mul_eq_mul_left hp this
    have hzero : ∀ x ∉ Set.range g, f x = 0 := by
      intro x hx
      have : ¬ p ∣ m + (x + 1) := fun h => hx ((hdiv x).1 h)
      simp only [f, if_neg this, zero_div]
    have hcomp : f ∘ g = fun t : ℕ => (1 / 2 : ℝ) ^ (k0 + 1) * ((1 / 2 : ℝ) ^ p) ^ t := by
      funext t
      have h1 : p ∣ m + (g t + 1) := (hdiv (g t)).2 ⟨t, rfl⟩
      simp only [Function.comp, f, if_pos h1, g]
      rw [← pow_mul, ← pow_add, one_div_pow, one_div]
      ring
    have hr0 : (0 : ℝ) ≤ (1 / 2 : ℝ) ^ p := by positivity
    have hr1 : (1 / 2 : ℝ) ^ p < 1 := pow_lt_one₀ (by norm_num) (by norm_num) hp.ne'
    have hgeo := (hasSum_geometric_of_lt_one hr0 hr1).mul_left ((1 / 2 : ℝ) ^ (k0 + 1))
    rw [← hcomp] at hgeo
    have hH := (hg.hasSum_iff hzero).1 hgeo
    change ∑' k : ℕ, f k = _
    rw [hH.tsum_eq]
    have hk : k0 + 1 = p - s := by omega
    rw [hk]
    have h2 : (2 : ℝ) ^ p = 2 ^ (p - s) * 2 ^ s := by rw [← pow_add, Nat.sub_add_cancel hsp.le]
    have h3 : (1 : ℝ) < 2 ^ p := one_lt_pow₀ (by norm_num) hp.ne'
    have h4 : (2 : ℝ) ^ p - 1 ≠ 0 := by linarith
    have h5 : (0 : ℝ) < 2 ^ (p - s) := by positivity
    rw [one_div_pow, one_div_pow]
    field_simp
    rw [h2]
  -- (ii) the dilation identity with the densities left as sums
  have hE0 : ∑' k : ℕ, (ω (a * (m + (k + 1))) : ℝ) / 2 ^ (k + 1)
      = ∑' k : ℕ, (ω (m + (k + 1)) : ℝ) / 2 ^ (k + 1) + (ω a : ℝ)
        - ∑ p ∈ a.primeFactors,
            ∑' k : ℕ, (if p ∣ m + (k + 1) then (1 : ℝ) else 0) / 2 ^ (k + 1) := by
    have hω : ∀ y : ℕ, ω y = y.primeFactors.card := fun y => by
      rw [ArithmeticFunction.cardDistinctFactors_apply, Nat.primeFactors, List.card_toFinset]
    -- (a) pointwise: ω (a x) = ω x + ω a - #{p ∣ a : p ∣ x}
    have hpt : ∀ x : ℕ, x ≠ 0 → (ω (a * x) : ℝ)
        = (ω x : ℝ) + (ω a : ℝ) - ∑ p ∈ a.primeFactors, (if p ∣ x then (1 : ℝ) else 0) := by
      intro x hx
      have hint : a.primeFactors ∩ x.primeFactors = a.primeFactors.filter (· ∣ x) := by
        ext p
        simp only [Finset.mem_inter, Finset.mem_filter, Nat.mem_primeFactors]
        constructor
        · rintro ⟨h1, h2⟩
          exact ⟨h1, h2.2.1⟩
        · rintro ⟨h1, h2⟩
          exact ⟨h1, h1.1, h2, hx⟩
      have hc := Finset.card_union_add_card_inter a.primeFactors x.primeFactors
      rw [hint, ← Nat.primeFactors_mul ha hx] at hc
      rw [Finset.sum_boole, hω, hω, hω]
      have hc' : ((a * x).primeFactors.card : ℝ) + ((a.primeFactors.filter (· ∣ x)).card : ℝ)
          = (a.primeFactors.card : ℝ) + (x.primeFactors.card : ℝ) := by exact_mod_cast hc
      linarith
    -- (b) summability: ω y ≤ y + 1, and y ≤ B (k + 1) along both sequences
    have hle : ∀ y : ℕ, ω y ≤ y + 1 := by
      intro y
      have hsub : y.primeFactors ⊆ Finset.range (y + 1) := by
        intro p hp
        have hp' := Nat.mem_primeFactors.1 hp
        exact Finset.mem_range.2 (Nat.lt_succ_of_le (Nat.le_of_dvd (Nat.pos_of_ne_zero hp'.2.2) hp'.2.1))
      have := Finset.card_le_card hsub
      rw [Finset.card_range] at this
      rw [hω]
      omega
    have hr : ‖(1 / 2 : ℝ)‖ < 1 := by norm_num
    have hS : Summable (fun k : ℕ => ((k : ℝ) + 1) * (1 / 2 : ℝ) ^ (k + 1)) := by
      have h0 := (hasSum_coe_mul_geometric_of_norm_lt_one hr).summable
      have h1 := (summable_nat_add_iff 1).2 h0
      simpa [Nat.cast_add, Nat.cast_one] using h1
    have hsumm : ∀ (g : ℕ → ℕ) (B : ℕ), (∀ k, g k ≤ B * (k + 1)) →
        Summable (fun k : ℕ => (ω (g k) : ℝ) / 2 ^ (k + 1)) := by
      intro g B hg
      refine Summable.of_nonneg_of_le (fun k => by positivity) (fun k => ?_) (hS.mul_left ((B : ℝ) + 1))
      have h1 : ω (g k) ≤ (B + 1) * (k + 1) := by
        have := hle (g k); have := hg k; nlinarith
      have h2 : (ω (g k) : ℝ) ≤ ((B : ℝ) + 1) * ((k : ℝ) + 1) := by exact_mod_cast h1
      have hp : (0 : ℝ) < 2 ^ (k + 1) := by positivity
      rw [div_le_iff₀ hp, one_div_pow, mul_assoc, mul_assoc, one_div_mul_cancel hp.ne', mul_one]
      exact h2
    have hA : Summable (fun k : ℕ => (ω (a * (m + (k + 1))) : ℝ) / 2 ^ (k + 1)) :=
      hsumm (fun k => a * (m + (k + 1))) (a * (m + 1)) (fun k => by
        have h : m + (k + 1) ≤ (m + 1) * (k + 1) := by nlinarith
        calc a * (m + (k + 1)) ≤ a * ((m + 1) * (k + 1)) := Nat.mul_le_mul_left a h
          _ = a * (m + 1) * (k + 1) := by ring)
    have hT : Summable (fun k : ℕ => (ω (m + (k + 1)) : ℝ) / 2 ^ (k + 1)) :=
      hsumm (fun k => m + (k + 1)) (m + 1) (fun k => by nlinarith)
    have hgeo : Summable (fun k : ℕ => (1 : ℝ) / 2 ^ (k + 1)) := by
      have := (summable_geometric_two).mul_left (1 / 2 : ℝ)
      refine this.congr (fun k => ?_)
      rw [one_div_pow, pow_succ]
      field_simp
    have hI : ∀ p ∈ a.primeFactors,
        Summable (fun k : ℕ => (if p ∣ m + (k + 1) then (1 : ℝ) else 0) / 2 ^ (k + 1)) := by
      intro p _
      refine Summable.of_nonneg_of_le (fun k => by positivity) (fun k => ?_) hgeo
      have hp : (0 : ℝ) < 2 ^ (k + 1) := by positivity
      apply div_le_div_of_nonneg_right _ hp.le
      split_ifs <;> norm_num
    -- (c) sum the pointwise identity
    have hC : ∑' k : ℕ, (ω a : ℝ) / 2 ^ (k + 1) = (ω a : ℝ) := by
      calc ∑' k : ℕ, (ω a : ℝ) / 2 ^ (k + 1) = ∑' k : ℕ, (ω a : ℝ) / 2 / 2 ^ k :=
            tsum_congr (fun k => by rw [pow_succ, div_div, mul_comm])
        _ = (ω a : ℝ) := tsum_geometric_two' _
    have hCs : Summable (fun k : ℕ => (ω a : ℝ) / 2 ^ (k + 1)) := by
      refine (hgeo.mul_left (ω a : ℝ)).congr (fun k => ?_)
      field_simp
    have hcongr : ∀ k : ℕ, (ω (a * (m + (k + 1))) : ℝ) / 2 ^ (k + 1)
        = ((ω (m + (k + 1)) : ℝ) / 2 ^ (k + 1) + (ω a : ℝ) / 2 ^ (k + 1))
          - ∑ p ∈ a.primeFactors, (if p ∣ m + (k + 1) then (1 : ℝ) else 0) / 2 ^ (k + 1) := by
      intro k
      rw [hpt _ (by omega), ← Finset.sum_div]
      ring
    rw [tsum_congr hcongr, Summable.tsum_sub (hT.add hCs) (summable_sum hI),
      Summable.tsum_add hT hCs, hC, Summable.tsum_finsetSum hI]
  rw [hE0]
  congr 1
  exact Finset.sum_congr rfl (fun p hp => hcl p m (Nat.pos_of_mem_primeFactors hp))
