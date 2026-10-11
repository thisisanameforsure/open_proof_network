import Mathlib
import Nodes.«spec-13f68833».Context

open scoped ArithmeticFunction.omega

/-! A speculative ingredient for erdos-69 (D-29): a linear bound on `ω` bounds the tail.
If `ω (n + 1 + k) ≤ C (k + 1)` for every `k`, then the tail
`∑' j, ω (n + 1 + j) / 2^(j+1)` (the same expression the nodes under erdos-69--h2-v2 use) is at
most `2 C`, because `∑_{j ≥ 0} (j + 1) / 2^(j+1) = 2`. The literature route
(Tao–Teräväinen, arXiv:2512.01739, abstract) gives infinitely many `n` with `ω (n + k) ≪ k`
for all `k ≥ 1`; with this lemma the tails at those `n` are bounded by a constant. That is a
bridge, not the hard step. -/

theorem Opn.erdos_69_tail_le_of_linear_bound :
    ∀ (n : ℕ) (C : ℝ), (∀ k : ℕ, (ω (n + 1 + k) : ℝ) ≤ C * ((k : ℝ) + 1)) →
      ∑' j : ℕ, (ω (n + 1 + j) : ℝ) / 2 ^ (j + 1) ≤ 2 * C := by
  intro n C hC
  have hsum0 : Summable (fun n : ℕ => (ω n : ℝ) / 2 ^ n) := by
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
  have hsA : Summable (fun k : ℕ => (ω (n + 1 + k) : ℝ) / 2 ^ (k + 1)) := by
    have h := ((summable_nat_add_iff (n + 1)).mpr hsum0).mul_left ((2 : ℝ) ^ n)
    refine h.congr (fun k => ?_)
    have hp : (2 : ℝ) ^ (k + (n + 1)) = 2 ^ (k + 1) * 2 ^ n := by
      rw [← pow_add]; ring_nf
    rw [hp, show k + (n + 1) = n + 1 + k by ring]
    field_simp
  -- the weights: ∑ (j+1)/2^(j+1) = 2
  have hH : HasSum (fun j : ℕ => ((j : ℝ) + 1) / 2 ^ (j + 1)) 2 := by
    have hr : ‖(1 / 2 : ℝ)‖ < 1 := by norm_num [Real.norm_eq_abs]
    have h := hasSum_coe_mul_geometric_of_norm_lt_one hr
    have h' := (hasSum_nat_add_iff' 1).mpr h
    have e : (1 / 2 : ℝ) / (1 - 1 / 2) ^ 2
        - ∑ i ∈ Finset.range 1, (i : ℝ) * (1 / 2) ^ i = 2 := by
      norm_num
    rw [e] at h'
    refine h'.congr_fun (fun j => ?_)
    push_cast
    rw [div_pow, one_pow, mul_one_div]
  have hS := hH.summable
  have hval := hH.tsum_eq
  have hle : ∀ j : ℕ, (ω (n + 1 + j) : ℝ) / 2 ^ (j + 1) ≤ C * (((j : ℝ) + 1) / 2 ^ (j + 1)) := by
    intro j
    rw [← mul_div_assoc]
    exact div_le_div_of_nonneg_right (hC j) (by positivity)
  calc ∑' j : ℕ, (ω (n + 1 + j) : ℝ) / 2 ^ (j + 1)
      ≤ ∑' j : ℕ, C * (((j : ℝ) + 1) / 2 ^ (j + 1)) :=
        Summable.tsum_le_tsum hle hsA (hS.mul_left C)
    _ = 2 * C := by rw [tsum_mul_left, hval, mul_comm]
