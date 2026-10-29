import Mathlib

open Nat

/-! Witness for A's `h_size` hole (shape `∀ a n k, P → Q`, so step 7 wants `∃ a n k, P`):
an interior solution, (n, k) = (256, 128), a = C(256,128). The threshold:
(log 256)^(5/6) = (8 log 2)^(5/6) ≤ 8 log 2 / 1.3 ≤ 7 log 2 = log 128, using 1.3^6 ≤ 8 log 2. -/

theorem witness : ∃ a n k : ℕ,
    1 ≤ k ∧ Real.exp (Real.log (n : ℝ) ^ (5 / 6 : ℝ)) ≤ (k : ℝ) ∧ 2 * k ≤ n ∧ n.choose k = a := by
  refine ⟨Nat.choose 256 128, 256, 128, by norm_num, ?_, by norm_num, rfl⟩
  have hl2 : (0.6931471803 : ℝ) < Real.log 2 := Real.log_two_gt_d9
  have hl2' : Real.log 2 < 0.6931471808 := Real.log_two_lt_d9
  have h256 : Real.log ((256 : ℕ) : ℝ) = 8 * Real.log 2 := by
    rw [show ((256 : ℕ) : ℝ) = (2 : ℝ) ^ (8 : ℕ) by norm_num, Real.log_pow]; norm_num
  have h128 : Real.log ((128 : ℕ) : ℝ) = 7 * Real.log 2 := by
    rw [show ((128 : ℕ) : ℝ) = (2 : ℝ) ^ (7 : ℕ) by norm_num, Real.log_pow]; norm_num
  set x : ℝ := 8 * Real.log 2 with hx
  have hx0 : 0 < x := by rw [hx]; positivity
  -- 1.3 ≤ x^(1/6) since 1.3^6 ≤ x
  have h6 : (1.3 : ℝ) ≤ x ^ ((1 : ℝ) / 6) := by
    have h1 : ((1.3 : ℝ) ^ (6 : ℕ)) ^ ((1 : ℝ) / 6) ≤ x ^ ((1 : ℝ) / 6) :=
      Real.rpow_le_rpow (by positivity) (by rw [hx]; norm_num; linarith) (by norm_num)
    rwa [← Real.rpow_natCast, ← Real.rpow_mul (by norm_num), show ((6 : ℕ) : ℝ) * ((1 : ℝ) / 6) = 1 by norm_num,
      Real.rpow_one] at h1
  -- x^(5/6) * x^(1/6) = x, so x^(5/6) ≤ x / 1.3
  have hsplit : x ^ ((5 : ℝ) / 6) * x ^ ((1 : ℝ) / 6) = x := by
    rw [← Real.rpow_add hx0]; norm_num
  have h56 : x ^ ((5 : ℝ) / 6) ≤ 7 * Real.log 2 := by
    have hp : 0 ≤ x ^ ((5 : ℝ) / 6) := Real.rpow_nonneg hx0.le _
    have : x ^ ((5 : ℝ) / 6) * 1.3 ≤ x := by
      calc x ^ ((5 : ℝ) / 6) * 1.3 ≤ x ^ ((5 : ℝ) / 6) * x ^ ((1 : ℝ) / 6) :=
            mul_le_mul_of_nonneg_left h6 hp
        _ = x := hsplit
    rw [hx] at this ⊢
    nlinarith
  rw [h256]
  calc Real.exp (x ^ ((5 : ℝ) / 6)) ≤ Real.exp (7 * Real.log 2) := Real.exp_le_exp.mpr h56
    _ = ((128 : ℕ) : ℝ) := by rw [← h128, Real.exp_log (by norm_num)]
