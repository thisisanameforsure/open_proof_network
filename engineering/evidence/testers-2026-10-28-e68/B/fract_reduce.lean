import Mathlib

/-- Next-level candidate: the integer parts N!/n! drop out of the fractional part. -/
theorem B_fract_reduce : ∀ N : ℕ,
    Int.fract (∑ n ∈ Finset.Icc 2 N, (N.factorial : ℝ) / ((n.factorial : ℝ) - 1)) =
      Int.fract (∑ n ∈ Finset.Icc 2 N,
        (N.factorial : ℝ) / ((n.factorial : ℝ) * ((n.factorial : ℝ) - 1))) := by
  intro N
  have hsplit : ∀ n ∈ Finset.Icc 2 N, (N.factorial : ℝ) / ((n.factorial : ℝ) - 1) =
      (((N.factorial / n.factorial : ℕ) : ℤ) : ℝ) +
        (N.factorial : ℝ) / ((n.factorial : ℝ) * ((n.factorial : ℝ) - 1)) := by
    intro n hn
    rw [Finset.mem_Icc] at hn
    have h2 : (2:ℕ) ≤ n.factorial := by simpa using Nat.factorial_le hn.1
    have h2' : (2:ℝ) ≤ (n.factorial : ℝ) := by exact_mod_cast h2
    have hd : n.factorial ∣ N.factorial := Nat.factorial_dvd_factorial hn.2
    have hc : ((N.factorial / n.factorial : ℕ) : ℝ) = (N.factorial : ℝ) / (n.factorial : ℝ) := by
      rw [Nat.cast_div hd (by positivity)]
    rw [Int.cast_natCast, hc]
    have h0 : (n.factorial : ℝ) ≠ 0 := by positivity
    have h1 : (n.factorial : ℝ) - 1 ≠ 0 := by linarith
    field_simp
    ring
  rw [Finset.sum_congr rfl hsplit, Finset.sum_add_distrib, ← Int.cast_sum, add_comm,
    Int.fract_add_intCast]
