import Mathlib

open Nat

/-! Elementary inputs of MRSTT Thm 1.3's deduction, prepared for A's --h3 skeleton (agent C, 2026-10-27).
Scratch form: plain theorems; they become `private` helpers under a hole's theorem when a hole needs them. -/

/-- (1.5), integer form: a left-half solution `C(n,m) = t` forces `4^m ≤ (2m+1) t`. -/
theorem Opn.e849_four_pow_le (n m t : ℕ) (h2 : 2 * m ≤ n) (ht : n.choose m = t) :
    4 ^ m ≤ (2 * m + 1) * t := by
  calc 4 ^ m ≤ (2 * m + 1) * (2 * m).choose m := Nat.four_pow_le_two_mul_add_one_mul_central_binom m
    _ ≤ (2 * m + 1) * n.choose m := Nat.mul_le_mul_left _ (Nat.choose_le_choose m h2)
    _ = (2 * m + 1) * t := by rw [ht]

/-- A left-half solution has `t ≥ 1`. -/
theorem Opn.e849_t_pos (n m t : ℕ) (h2 : 2 * m ≤ n) (ht : n.choose m = t) : 0 < t := by
  rw [← ht]; exact Nat.choose_pos (by omega)

/-- (1.5), real form: `m log 4 ≤ log (2m+1) + log t`. -/
theorem Opn.e849_m_log_four_le (n m t : ℕ) (h2 : 2 * m ≤ n) (ht : n.choose m = t) :
    (m : ℝ) * Real.log 4 ≤ Real.log (2 * m + 1) + Real.log t := by
  have h := Opn.e849_four_pow_le n m t h2 ht
  have ht0 : 0 < t := Opn.e849_t_pos n m t h2 ht
  have hcast : ((4 : ℝ) ^ m) ≤ (2 * (m : ℝ) + 1) * (t : ℝ) := by exact_mod_cast h
  have hlog := Real.log_le_log (by positivity) hcast
  rw [Real.log_pow, Real.log_mul (by positivity) (by exact_mod_cast ht0.ne')] at hlog
  exact hlog

/-- `2m + 1 ≤ 2^m` for `m ≥ 3`. -/
theorem Opn.e849_two_mul_add_one_le_two_pow (m : ℕ) (hm : 3 ≤ m) : 2 * m + 1 ≤ 2 ^ m := by
  induction m with
  | zero => omega
  | succ k ih =>
    rcases Nat.lt_or_ge k 3 with hk | hk
    · interval_cases k <;> simp_all
    · have := ih hk
      rw [pow_succ]; omega

/-- (1.5), clean form: for `m ≥ 3` a left-half solution has `2^m ≤ t`, so `m ≤ log₂ t`. -/
theorem Opn.e849_two_pow_le (n m t : ℕ) (h2 : 2 * m ≤ n) (ht : n.choose m = t) (hm : 3 ≤ m) :
    2 ^ m ≤ t := by
  have h := Opn.e849_four_pow_le n m t h2 ht
  have h4 : (4 : ℕ) ^ m = 2 ^ m * 2 ^ m := by rw [← mul_pow]; norm_num
  have hb := Opn.e849_two_mul_add_one_le_two_pow m hm
  have hpos : 0 < 2 ^ m := by positivity
  rw [h4] at h
  by_contra hlt
  have hlt := Nat.lt_of_not_le hlt
  have : (2 * m + 1) * t < 2 ^ m * 2 ^ m :=
    calc (2 * m + 1) * t < (2 * m + 1) * 2 ^ m := Nat.mul_lt_mul_of_pos_left hlt (by omega)
      _ ≤ 2 ^ m * 2 ^ m := Nat.mul_le_mul_right _ hb
  omega

theorem Opn.e849_m_le_log_two (n m t : ℕ) (h2 : 2 * m ≤ n) (ht : n.choose m = t) (hm : 3 ≤ m) :
    m ≤ Nat.log 2 t :=
  Nat.le_log_of_pow_le (by norm_num) (Opn.e849_two_pow_le n m t h2 ht hm)

/-- Strict monotonicity in `n` at fixed `k ≥ 1`: `C(n,k) < C(n+1,k)` once `k ≤ n`. -/
theorem Opn.e849_choose_lt_succ_left (n k : ℕ) (hk : 1 ≤ k) (hkn : k ≤ n) :
    n.choose k < (n + 1).choose k := by
  obtain ⟨j, rfl⟩ : ∃ j, k = j + 1 := ⟨k - 1, by omega⟩
  rw [Nat.choose_succ_succ']
  have : 0 < n.choose j := Nat.choose_pos (by omega)
  omega

theorem Opn.e849_choose_lt_left (n n' k : ℕ) (hk : 1 ≤ k) (hkn : k ≤ n) (hnn : n < n') :
    n.choose k < n'.choose k := by
  induction n' with
  | zero => omega
  | succ p ih =>
    rcases Nat.lt_succ_iff_lt_or_eq.mp hnn with h | h
    · exact lt_trans (ih h) (Opn.e849_choose_lt_succ_left p k hk (by omega))
    · subst h; exact Opn.e849_choose_lt_succ_left n k hk hkn

/-- Two left-half solutions in the same column `k ≥ 1` are the same row. -/
theorem Opn.e849_same_column (n n' k t : ℕ) (hk : 1 ≤ k) (hkn : k ≤ n) (hkn' : k ≤ n')
    (h : n.choose k = t) (h' : n'.choose k = t) : n = n' := by
  by_contra hne
  rcases lt_or_gt_of_ne hne with hlt | hlt
  · have := Opn.e849_choose_lt_left n n' k hk hkn hlt; omega
  · have := Opn.e849_choose_lt_left n' n k hk hkn' hlt; omega

/-- Strict monotonicity in `k` below the middle: `j < n/2 → C(n,j) < C(n,j+1)`. -/
theorem Opn.e849_choose_lt_succ_right (n j : ℕ) (hj : j < n / 2) : n.choose j < n.choose (j + 1) := by
  have key := Nat.choose_succ_right_eq n j
  have hpos : 0 < n.choose j := Nat.choose_pos (by omega)
  have hnj : j + 2 ≤ n - j := by omega
  by_contra hle
  have hle := Nat.le_of_not_lt hle
  have : n.choose (j + 1) * (j + 1) < n.choose j * (n - j) :=
    calc n.choose (j + 1) * (j + 1) ≤ n.choose j * (j + 1) := Nat.mul_le_mul_right _ hle
      _ < n.choose j * (n - j) := Nat.mul_lt_mul_of_pos_left (by omega) hpos
  omega

theorem Opn.e849_choose_lt_right (n j m : ℕ) (hjm : j < m) (hm : 2 * m ≤ n) :
    n.choose j < n.choose m := by
  induction m with
  | zero => omega
  | succ p ih =>
    rcases Nat.lt_succ_iff_lt_or_eq.mp hjm with h | h
    · exact lt_trans (ih h (by omega)) (Opn.e849_choose_lt_succ_right n p (by omega))
    · subst h; exact Opn.e849_choose_lt_succ_right n j (by omega)

/-- MRSTT deduction step 1: if `(n, m)` and `(n', m')` are left-half solutions of `C(·,·) = t`
with `m' < m`, then `n < n'`. (With `m` maximal, every other solution is to the lower right.) -/
theorem Opn.e849_other_solution_right (n m n' m' t : ℕ) (hm : 2 * m ≤ n) (_hm' : 2 * m' ≤ n')
    (h : n.choose m = t) (h' : n'.choose m' = t) (hlt : m' < m) : n < n' := by
  by_contra hle
  have hle := Nat.le_of_not_lt hle
  have h1 : n'.choose m' ≤ n.choose m' := Nat.choose_le_choose m' hle
  have h2 : n.choose m' < n.choose m := Opn.e849_choose_lt_right n m' m hlt hm
  omega

/-- Step 1 packaged: among left-half solutions with `m` maximal, any other solution has
`m' < m` and `n' > n`. -/
theorem Opn.e849_maximal_step (n m n' m' t : ℕ) (hm : 2 * m ≤ n) (hm' : 2 * m' ≤ n')
    (h : n.choose m = t) (h' : n'.choose m' = t) (h1 : 1 ≤ m') (hmax : m' ≤ m)
    (hne : (n, m) ≠ (n', m')) : m' < m ∧ n < n' := by
  rcases Nat.lt_or_ge m' m with hlt | hge
  · exact ⟨hlt, Opn.e849_other_solution_right n m n' m' t hm hm' h h' hlt⟩
  · have hmm : m' = m := le_antisymm hmax hge
    subst hmm
    have := Opn.e849_same_column n n' m' t h1 (by omega) (by omega) h h'
    exact absurd (by rw [this]) hne
