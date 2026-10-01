import Mathlib
import Nodes.«spec-9f8cb4ea».Context

open scoped ArithmeticFunction.omega

/-! A speculative ingredient for erdos-69 (D-29): the composite-dilation identity for the tails,
in closed form. For `a ≠ 0` and every `m`,
`∑' k, ω (a (m+k+1)) / 2^(k+1) = ∑' k, ω (m+k+1) / 2^(k+1) + ω a
  − ∑_{p ∣ a prime} 2^(m mod p) / (2^p − 1)`.
Pointwise it is `ω (a x) + #{p ∣ a : p ∣ x} = ω a + ω x` (inclusion–exclusion on prime
factors), summed against `1/2^(k+1)`; the multiples of `p` among `m+1, m+2, …` carry binary
weight exactly `2^(m mod p) / (2^p − 1)`. So a dilated tail differs from the tail itself by a
rational number with denominator dividing `∏_{p ∣ a} (2^p − 1)`: if `∑ ω(n)/2^n` were rational,
a fixed integer multiple of every dilated tail would be an integer as well. 69-C reports
(annex on erdos-69, graph PR #256) that an external formal proof of Erdős 69 rests on a
dilation identity of this kind. The identity alone proves nothing about irrationality. -/

theorem Opn.erdos_69_dilated_tail_closed :
    ∀ (a m : ℕ), a ≠ 0 →
      ∑' k : ℕ, (ω (a * (m + (k + 1))) : ℝ) / 2 ^ (k + 1)
        = ∑' k : ℕ, (ω (m + (k + 1)) : ℝ) / 2 ^ (k + 1) + (ω a : ℝ)
          - ∑ p ∈ a.primeFactors, (2 : ℝ) ^ (m % p) / (2 ^ p - 1) := by
  intro a m ha
  have hind : ∀ p m : ℕ, 0 < p →
      ∑' k : ℕ, (if p ∣ m + (k + 1) then (1 : ℝ) else 0) / 2 ^ (k + 1)
        = (2 : ℝ) ^ (m % p) / (2 ^ p - 1) := by
    intro p m hp
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
  have hdt :
      ∑' k : ℕ, (ω (a * (m + (k + 1))) : ℝ) / 2 ^ (k + 1)
        = ∑' k : ℕ, (ω (m + (k + 1)) : ℝ) / 2 ^ (k + 1) + (ω a : ℝ)
          - ∑ p ∈ a.primeFactors,
              ∑' k : ℕ, (if p ∣ m + (k + 1) then (1 : ℝ) else 0) / 2 ^ (k + 1) := by
    have hω : ∀ x : ℕ, ω x = x.primeFactors.card := fun x => by
      rw [ArithmeticFunction.cardDistinctFactors_apply]; rfl
    have hmul : ∀ n : ℕ, n ≠ 0 → (ω (a * n) : ℝ) = (ω n : ℝ) + (ω a : ℝ)
        - ∑ p ∈ a.primeFactors, (if p ∣ n then (1 : ℝ) else 0) := by
      intro n hn
      have hunion : (a * n).primeFactors.card + (a.primeFactors ∩ n.primeFactors).card
          = a.primeFactors.card + n.primeFactors.card := by
        rw [Nat.primeFactors_mul ha hn, Finset.card_union_add_card_inter]
      have hinter : a.primeFactors ∩ n.primeFactors = a.primeFactors.filter (· ∣ n) := by
        ext p
        simp only [Finset.mem_inter, Finset.mem_filter, Nat.mem_primeFactors]
        constructor
        · rintro ⟨h1, h2⟩; exact ⟨h1, h2.2.1⟩
        · rintro ⟨h1, h2⟩; exact ⟨h1, h1.1, h2, hn⟩
      have hsum : (∑ p ∈ a.primeFactors, (if p ∣ n then (1 : ℝ) else 0))
          = ((a.primeFactors.filter (· ∣ n)).card : ℝ) := by
        rw [Finset.card_filter]; push_cast; rfl
      rw [hsum, ← hinter, hω, hω, hω]
      have : ((a * n).primeFactors.card : ℝ) + ((a.primeFactors ∩ n.primeFactors).card : ℝ)
          = (a.primeFactors.card : ℝ) + (n.primeFactors.card : ℝ) := by exact_mod_cast hunion
      linarith
    have hsum0 : Summable (fun n : ℕ => (ω n : ℝ) / 2 ^ n) := by
      have hbound : ∀ n : ℕ,
          (ω n : ℝ) / 2 ^ n ≤ (n : ℝ) ^ 1 * (1 / 2 : ℝ) ^ n + (1 / 2 : ℝ) ^ n := by
        intro n
        have h1 : ω n ≤ n + 1 := by
          rw [hω]
          calc n.primeFactors.card ≤ (Finset.range (n + 1)).card :=
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
    have hsA : Summable (fun k : ℕ => (ω (m + (k + 1)) : ℝ) / 2 ^ (k + 1)) := by
      have h := ((summable_nat_add_iff (m + 1)).mpr hsum0).mul_left ((2 : ℝ) ^ m)
      refine h.congr (fun k => ?_)
      rw [show k + (m + 1) = m + (k + 1) by ring, show m + (k + 1) = (k + 1) + m by ring,
        pow_add]
      field_simp
    have hgeo : Summable (fun k : ℕ => (1 : ℝ) / 2 ^ (k + 1)) := by
      refine (summable_geometric_two.mul_left (1 / 2 : ℝ)).congr (fun k => ?_)
      rw [one_div, one_div, ← inv_pow, pow_succ, mul_comm]
    have h1 : ∑' k : ℕ, (1 : ℝ) / 2 ^ (k + 1) = 1 := by
      calc ∑' k : ℕ, (1 : ℝ) / 2 ^ (k + 1) = ∑' n : ℕ, (1 : ℝ) / 2 / 2 ^ n :=
            tsum_congr (fun k => by ring)
        _ = 1 := tsum_geometric_two' 1
    have hsI : ∀ p ∈ a.primeFactors,
        Summable (fun k : ℕ => (if p ∣ m + (k + 1) then (1 : ℝ) else 0) / 2 ^ (k + 1)) := by
      intro p _
      refine Summable.of_nonneg_of_le (fun k => ?_) (fun k => ?_) hgeo
      · split_ifs <;> positivity
      · split_ifs
        · exact le_rfl
        · rw [zero_div]; positivity
    have hpt : ∀ k : ℕ, (ω (a * (m + (k + 1))) : ℝ) / 2 ^ (k + 1)
        = ((ω (m + (k + 1)) : ℝ) / 2 ^ (k + 1) + (ω a : ℝ) * (1 / 2 ^ (k + 1)))
          - ∑ p ∈ a.primeFactors, (if p ∣ m + (k + 1) then (1 : ℝ) else 0) / 2 ^ (k + 1) := by
      intro k
      rw [hmul _ (by omega), ← Finset.sum_div]
      ring
    rw [tsum_congr hpt, (hsA.add (hgeo.mul_left _)).tsum_sub (summable_sum hsI),
      hsA.tsum_add (hgeo.mul_left _), tsum_mul_left, h1, Summable.tsum_finsetSum hsI, mul_one]
  rw [hdt]
  congr 1
  refine Finset.sum_congr rfl (fun p hp => ?_)
  exact hind p m (Nat.pos_of_mem_primeFactors hp)
