import Mathlib

open scoped ArithmeticFunction.omega

theorem Opn.erdos_69_one_le_tail :
    ∀ n : ℕ, 1 ≤ n → 1 ≤ ∑' j : ℕ, (ω (n + 1 + j) : ℝ) / 2 ^ (j + 1) := by
  intro n hn
  have hω : ∀ y : ℕ, ω y = y.primeFactors.card := fun y => by
    rw [ArithmeticFunction.cardDistinctFactors_apply, Nat.primeFactors, List.card_toFinset]
  have hle : ∀ y : ℕ, ω y ≤ y + 1 := by
    intro y
    have hsub : y.primeFactors ⊆ Finset.range (y + 1) := by
      intro p hp
      have hp' := Nat.mem_primeFactors.1 hp
      exact Finset.mem_range.2 (Nat.lt_succ_of_le (Nat.le_of_dvd (Nat.pos_of_ne_zero hp'.2.2) hp'.2.1))
    have := Finset.card_le_card hsub
    rw [Finset.card_range] at this
    rw [hω]; omega
  have hone : ∀ j : ℕ, 1 ≤ ω (n + 1 + j) := by
    intro j
    rw [hω]
    apply Finset.card_pos.2
    exact ⟨(n + 1 + j).minFac, Nat.mem_primeFactors.2
      ⟨Nat.minFac_prime (by omega), Nat.minFac_dvd _, by omega⟩⟩
  have hr : ‖(1 / 2 : ℝ)‖ < 1 := by norm_num
  have hS : Summable (fun k : ℕ => ((k : ℝ) + 1) * (1 / 2 : ℝ) ^ (k + 1)) := by
    have h0 := (hasSum_coe_mul_geometric_of_norm_lt_one hr).summable
    have h1 := (summable_nat_add_iff 1).2 h0
    simpa [Nat.cast_add, Nat.cast_one] using h1
  have hsum : Summable (fun j : ℕ => (ω (n + 1 + j) : ℝ) / 2 ^ (j + 1)) := by
    refine Summable.of_nonneg_of_le (fun k => by positivity) (fun k => ?_) (hS.mul_left ((n : ℝ) + 2))
    have h1 : ω (n + 1 + k) ≤ (n + 2) * (k + 1) := by have := hle (n + 1 + k); nlinarith
    have h2 : (ω (n + 1 + k) : ℝ) ≤ ((n : ℝ) + 2) * ((k : ℝ) + 1) := by exact_mod_cast h1
    have hp : (0 : ℝ) < 2 ^ (k + 1) := by positivity
    rw [div_le_iff₀ hp, one_div_pow, mul_assoc, mul_assoc, one_div_mul_cancel hp.ne', mul_one]
    exact h2
  have hgeo : HasSum (fun j : ℕ => (1 : ℝ) / 2 ^ (j + 1)) 1 := by
    have := (hasSum_geometric_two).mul_left (1 / 2 : ℝ)
    rw [show (1 / 2 : ℝ) * 2 = 1 by norm_num] at this
    refine this.congr_fun (fun k => ?_)
    rw [one_div_pow, pow_succ]; field_simp
  have := hasSum_le (fun j => ?_) hgeo hsum.hasSum
  · exact this
  · have hp : (0 : ℝ) < 2 ^ (j + 1) := by positivity
    apply div_le_div_of_nonneg_right _ hp.le
    exact_mod_cast hone j
