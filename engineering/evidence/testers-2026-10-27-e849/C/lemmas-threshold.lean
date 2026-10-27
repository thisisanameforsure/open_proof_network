import Mathlib

open Nat

/-! The interior threshold, unpacked (agent C, 2026-10-27): inside --h3's region
`exp((log n)^(5/6)) ≤ k`, so `log n ≤ (log k)^(6/5)`, and with (1.5) `n` is bounded in `t`. -/

/-- From `exp((log n)^(5/6)) ≤ k` (n, k naturals, n ≥ 1): `(log n)^(5/6) ≤ log k`. -/
theorem Opn.e849_threshold_log (n k : ℕ) (_hn : 1 ≤ n)
    (h : Real.exp (Real.log (n : ℝ) ^ ((5 : ℝ) / 6)) ≤ (k : ℝ)) :
    Real.log (n : ℝ) ^ ((5 : ℝ) / 6) ≤ Real.log (k : ℝ) := by
  have hk : (0 : ℝ) < k := lt_of_lt_of_le (Real.exp_pos _) h
  have := Real.log_le_log (Real.exp_pos _) h
  rwa [Real.log_exp] at this

/-- Inside the interior region, `log n ≤ (log k)^(6/5)`. -/
theorem Opn.e849_log_n_le (n k : ℕ) (hn : 1 ≤ n)
    (h : Real.exp (Real.log (n : ℝ) ^ ((5 : ℝ) / 6)) ≤ (k : ℝ)) :
    Real.log (n : ℝ) ≤ Real.log (k : ℝ) ^ ((6 : ℝ) / 5) := by
  have h1 := Opn.e849_threshold_log n k hn h
  have hln : 0 ≤ Real.log (n : ℝ) := Real.log_nonneg (by exact_mod_cast hn)
  have h2 : (Real.log (n : ℝ) ^ ((5 : ℝ) / 6)) ^ ((6 : ℝ) / 5) ≤ Real.log (k : ℝ) ^ ((6 : ℝ) / 5) :=
    Real.rpow_le_rpow (by positivity) h1 (by norm_num)
  rwa [← Real.rpow_mul hln, show ((5 : ℝ) / 6) * ((6 : ℝ) / 5) = 1 by norm_num, Real.rpow_one] at h2

/-- Inside the interior region, `n ≤ exp ((log k)^(6/5))`. -/
theorem Opn.e849_n_le_exp (n k : ℕ) (hn : 1 ≤ n)
    (h : Real.exp (Real.log (n : ℝ) ^ ((5 : ℝ) / 6)) ≤ (k : ℝ)) :
    (n : ℝ) ≤ Real.exp (Real.log (k : ℝ) ^ ((6 : ℝ) / 5)) := by
  have := Opn.e849_log_n_le n k hn h
  calc (n : ℝ) = Real.exp (Real.log (n : ℝ)) := (Real.exp_log (by exact_mod_cast hn)).symm
    _ ≤ Real.exp (Real.log (k : ℝ) ^ ((6 : ℝ) / 5)) := Real.exp_le_exp.mpr this

/-- The region is empty for `n = 0` and `n = 1` is excluded by `2k ≤ n`, `k ≥ 1`: a row in --h3's set
has `k ≥ 1`, `2k ≤ n`, so `n ≥ 2`. Combined with (1.5): `log k ≤ log (Nat.log 2 t)` once `k ≥ 3`. -/
theorem Opn.e849_log_k_le (n k t : ℕ) (h2 : 2 * k ≤ n) (ht : n.choose k = t) (hk : 3 ≤ k) :
    Real.log (k : ℝ) ≤ Real.log ((Nat.log 2 t : ℕ) : ℝ) := by
  have hkl : k ≤ Nat.log 2 t :=
    Nat.le_log_of_pow_le (by norm_num) (by
      have h := Nat.four_pow_le_two_mul_add_one_mul_central_binom k
      have h' : 4 ^ k ≤ (2 * k + 1) * t := by
        calc 4 ^ k ≤ (2 * k + 1) * (2 * k).choose k := h
          _ ≤ (2 * k + 1) * n.choose k := Nat.mul_le_mul_left _ (Nat.choose_le_choose k h2)
          _ = (2 * k + 1) * t := by rw [ht]
      have hb : 2 * k + 1 ≤ 2 ^ k := by
        clear h h' ht h2 n t
        induction k with
        | zero => omega
        | succ j ih =>
          rcases Nat.lt_or_ge j 3 with hj | hj
          · interval_cases j <;> simp_all
          · have := ih hj; rw [pow_succ]; omega
      have h4 : (4 : ℕ) ^ k = 2 ^ k * 2 ^ k := by rw [← mul_pow]; norm_num
      rw [h4] at h'
      by_contra hlt
      have hlt := Nat.lt_of_not_le hlt
      have : (2 * k + 1) * t < 2 ^ k * 2 ^ k :=
        calc (2 * k + 1) * t < (2 * k + 1) * 2 ^ k := Nat.mul_lt_mul_of_pos_left hlt (by omega)
          _ ≤ 2 ^ k * 2 ^ k := Nat.mul_le_mul_right _ hb
      omega)
  exact Real.log_le_log (by exact_mod_cast (show 0 < k by omega)) (by exact_mod_cast hkl)
