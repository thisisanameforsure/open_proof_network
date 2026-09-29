import Mathlib

open scoped ArithmeticFunction.omega

theorem Opn.erdos_69_tail_le_of_linear_bound :
    ∀ (n : ℕ) (C : ℝ), (∀ k : ℕ, (ω (n + 1 + k) : ℝ) ≤ C * ((k : ℝ) + 1)) →
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
