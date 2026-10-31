import Mathlib

theorem summ : Summable (fun n : ℕ => 1 / ((n + 2).factorial - 1 : ℝ)) := by
  have hf : Summable (fun n : ℕ => 2 * (1 / ((n + 2).factorial : ℝ))) := by
    have h := Real.summable_pow_div_factorial 1
    have h2 := (summable_nat_add_iff 2).mpr h
    simpa using h2.mul_left 2
  refine Summable.of_nonneg_of_le (fun n => ?_) (fun n => ?_) hf
  · have : 2 ≤ (n + 2).factorial := by
      calc 2 = (2 : ℕ).factorial := rfl
        _ ≤ (n + 2).factorial := Nat.factorial_le (by omega)
    have : (2 : ℝ) ≤ ((n + 2).factorial : ℝ) := by exact_mod_cast this
    apply div_nonneg zero_le_one; linarith
  · have : 2 ≤ (n + 2).factorial := by
      calc 2 = (2 : ℕ).factorial := rfl
        _ ≤ (n + 2).factorial := Nat.factorial_le (by omega)
    have h2 : (2 : ℝ) ≤ ((n + 2).factorial : ℝ) := by exact_mod_cast this
    rw [mul_one_div, div_le_div_iff₀ (by linarith) (by linarith)]
    linarith
