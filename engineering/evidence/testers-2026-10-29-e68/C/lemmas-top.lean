import Mathlib

/-- Consecutive scaled terms N!/(n!(n!−1)) at least halve once n ≥ 2. -/
theorem C_term_halves (A : ℝ) (hA : 0 ≤ A) (n : ℕ) (hn : 2 ≤ n) :
    A / (((n + 1).factorial : ℝ) * (((n + 1).factorial : ℝ) - 1)) ≤
      A / ((n.factorial : ℝ) * ((n.factorial : ℝ) - 1)) / 2 := by
  have hf2 : (2:ℝ) ≤ (n.factorial : ℝ) := by exact_mod_cast (by simpa using Nat.factorial_le hn)
  have hs : ((n + 1).factorial : ℝ) = ((n : ℝ) + 1) * (n.factorial : ℝ) := by
    rw [Nat.factorial_succ]; push_cast; ring
  have hn' : (2:ℝ) ≤ n := by exact_mod_cast hn
  have hD : 0 < (n.factorial : ℝ) * ((n.factorial : ℝ) - 1) := by nlinarith
  rw [div_div]
  apply div_le_div_of_nonneg_left hA (by positivity)
  rw [hs]
  nlinarith [mul_le_mul_of_nonneg_left hn' (le_of_lt (lt_of_lt_of_le (by norm_num) hf2))]

/-- The terms N!/(n!(n!−1)) for n from K to N sum to at most twice the n = K term (K ≥ 2). -/
theorem C_top_sum (N K : ℕ) (hK : 2 ≤ K) :
    ∑ n ∈ Finset.Icc K N, (N.factorial : ℝ) / ((n.factorial : ℝ) * ((n.factorial : ℝ) - 1)) ≤
      2 * ((N.factorial : ℝ) / ((K.factorial : ℝ) * ((K.factorial : ℝ) - 1))) := by
  set t : ℕ → ℝ := fun n => (N.factorial : ℝ) / ((n.factorial : ℝ) * ((n.factorial : ℝ) - 1)) with htdef
  have hA : (0:ℝ) ≤ N.factorial := by positivity
  have ht : ∀ j : ℕ, t (K + j) ≤ t K * (1 / 2) ^ j := by
    intro j
    induction j with
    | zero => simp
    | succ j ih =>
      have h := C_term_halves (N.factorial : ℝ) hA (K + j) (by omega)
      calc t (K + (j + 1)) = t (K + j + 1) := by rw [Nat.add_succ]
        _ ≤ t (K + j) / 2 := h
        _ ≤ t K * (1 / 2) ^ j / 2 := by gcongr
        _ = t K * (1 / 2) ^ (j + 1) := by ring
  have htK : 0 ≤ t K := by
    have hf2 : (2:ℝ) ≤ (K.factorial : ℝ) := by exact_mod_cast (by simpa using Nat.factorial_le hK)
    apply div_nonneg hA; nlinarith
  rw [show Finset.Icc K N = Finset.Ico K (N + 1) from rfl, Finset.sum_Ico_eq_sum_range]
  calc ∑ j ∈ Finset.range (N + 1 - K), t (K + j)
      ≤ ∑ j ∈ Finset.range (N + 1 - K), t K * (1 / 2) ^ j := Finset.sum_le_sum (fun j _ => ht j)
    _ = t K * ∑ j ∈ Finset.range (N + 1 - K), (1 / 2 : ℝ) ^ j := by rw [Finset.mul_sum]
    _ ≤ t K * 2 := by gcongr; exact sum_geometric_two_le _
    _ = 2 * t K := by ring
