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
    ∀ (n : ℕ) (C : ℝ), (∀ i : ℕ, (ω (n + 1 + i) : ℝ) ≤ C * ((i : ℝ) + 1)) →
      ∑' j : ℕ, (ω (n + 1 + j) : ℝ) / 2 ^ (j + 1) ≤ 2 * C := by
  intro n C h
  have hr : ‖(1 / 2 : ℝ)‖ < 1 := by norm_num
  -- Σ_{j ≥ 0} (j + 1) (1/2)^(j+1) = Σ_{m ≥ 0} m (1/2)^m = 2
  have hS : HasSum (fun j : ℕ => ((j : ℝ) + 1) * (1 / 2 : ℝ) ^ (j + 1)) 2 := by
    have h0 := hasSum_coe_mul_geometric_of_norm_lt_one hr
    have h1 := (hasSum_nat_add_iff' 1).mpr h0
    have e : (1 / 2 : ℝ) / (1 - 1 / 2) ^ 2 - ∑ i ∈ Finset.range 1, (i : ℝ) * (1 / 2) ^ i = 2 := by
      norm_num
    rw [e] at h1
    simpa [Nat.cast_add, Nat.cast_one] using h1
  have hg : HasSum (fun j : ℕ => C * (((j : ℝ) + 1) * (1 / 2 : ℝ) ^ (j + 1))) (C * 2) :=
    hS.mul_left C
  have hfg : ∀ j : ℕ, (ω (n + 1 + j) : ℝ) / 2 ^ (j + 1)
      ≤ C * (((j : ℝ) + 1) * (1 / 2 : ℝ) ^ (j + 1)) := by
    intro j
    have hp : (0 : ℝ) ≤ (1 / 2 : ℝ) ^ (j + 1) := by positivity
    have e : (ω (n + 1 + j) : ℝ) / 2 ^ (j + 1) = (ω (n + 1 + j) : ℝ) * (1 / 2 : ℝ) ^ (j + 1) := by
      rw [one_div_pow, div_eq_mul_one_div]
    rw [e, ← mul_assoc]
    exact mul_le_mul_of_nonneg_right (h j) hp
  have hf0 : ∀ j : ℕ, (0 : ℝ) ≤ (ω (n + 1 + j) : ℝ) / 2 ^ (j + 1) := fun j => by positivity
  have hf : Summable (fun j : ℕ => (ω (n + 1 + j) : ℝ) / 2 ^ (j + 1)) :=
    Summable.of_nonneg_of_le hf0 hfg hg.summable
  have := hasSum_le hfg hf.hasSum hg
  linarith
