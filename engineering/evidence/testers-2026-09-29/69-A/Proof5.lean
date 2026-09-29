import Mathlib
import Nodes.«spec-f1cadf9f».Context

open scoped ArithmeticFunction.omega

/-! A speculative ingredient for erdos-69 (D-29): the composite-dilation identity for the tails.
For `a ≠ 0`, dilating a tail by `a` changes it by `ω a` minus, for each prime `p ∣ a`, the
binary-weighted density of the terms `m + k + 1` that `p` divides:
`∑' k, ω (a (m+k+1)) / 2^(k+1) = ∑' k, ω (m+k+1) / 2^(k+1) + ω a
  - ∑_{p ∣ a} ∑' k, [p ∣ m+k+1] / 2^(k+1)`.
Pointwise it is `ω (a x) + #{p ∣ a : p ∣ x} = ω a + ω x` (inclusion–exclusion on prime
factors), summed against `1/2^(k+1)`. 69-C reports (annex on erdos-69, graph PR #256) that an
external formal proof of Erdős 69 rests on this identity; with rationality making a fixed
multiple of every tail an integer, it constrains dilated tails too. The identity alone proves
nothing about irrationality. -/

theorem Opn.erdos_69_dilated_tail :
    ∀ (a m : ℕ), a ≠ 0 →
      ∑' k : ℕ, (ω (a * (m + (k + 1))) : ℝ) / 2 ^ (k + 1)
        = ∑' k : ℕ, (ω (m + (k + 1)) : ℝ) / 2 ^ (k + 1) + (ω a : ℝ)
          - ∑ p ∈ a.primeFactors,
              ∑' k : ℕ, (if p ∣ m + (k + 1) then (1 : ℝ) else 0) / 2 ^ (k + 1) := by
  intro a m ha
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
