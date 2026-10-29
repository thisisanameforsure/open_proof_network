import Mathlib

/-- One summand of F_N splits as an integer plus r/(n!−1), r = (N!/n!) mod (n!−1). -/
theorem C_term_split (N n : ℕ) (h2 : 2 ≤ n) (hnN : n ≤ N) :
    (N.factorial : ℝ) / ((n.factorial : ℝ) - 1) =
      (((N.factorial / n.factorial + (N.factorial / n.factorial) / (n.factorial - 1) : ℕ) : ℤ) : ℝ) +
        (((N.factorial / n.factorial) % (n.factorial - 1) : ℕ) : ℝ) / ((n.factorial : ℝ) - 1) := by
  have hf2 : 2 ≤ n.factorial := by simpa using Nat.factorial_le h2
  set m := N.factorial / n.factorial with hm
  set d := n.factorial - 1 with hd
  have hNm : N.factorial = n.factorial * m := (Nat.mul_div_cancel' (Nat.factorial_dvd_factorial hnN)).symm
  have hdr : ((d : ℕ) : ℝ) = (n.factorial : ℝ) - 1 := by
    rw [hd, Nat.cast_sub (by omega)]; simp
  have hdpos : (0:ℝ) < (n.factorial : ℝ) - 1 := by
    have : (2:ℝ) ≤ (n.factorial : ℝ) := by exact_mod_cast hf2
    linarith
  have hqr : ((m : ℕ) : ℝ) = (d : ℝ) * ((m / d : ℕ) : ℝ) + ((m % d : ℕ) : ℝ) := by
    have := Nat.div_add_mod m d
    exact_mod_cast this.symm
  rw [Int.cast_natCast, Nat.cast_add, hNm, Nat.cast_mul]
  rw [hdr] at hqr
  have key : (n.factorial : ℝ) * (m : ℝ) =
      ((m : ℝ) + ((m / d : ℕ) : ℝ)) * ((n.factorial : ℝ) - 1) + ((m % d : ℕ) : ℝ) := by
    linear_combination hqr
  rw [key, add_div, mul_div_cancel_right₀ _ hdpos.ne']

/-- fract(F_N) is the fractional part of Σ_{n=2}^N r_n/(n!−1), r_n = (N!/n!) mod (n!−1). -/
theorem C_fract_mod (N : ℕ) :
    Int.fract (∑ n ∈ Finset.Icc 2 N, (N.factorial : ℝ) / ((n.factorial : ℝ) - 1)) =
      Int.fract (∑ n ∈ Finset.Icc 2 N,
        (((N.factorial / n.factorial) % (n.factorial - 1) : ℕ) : ℝ) / ((n.factorial : ℝ) - 1)) := by
  have hs : ∀ n ∈ Finset.Icc 2 N, (N.factorial : ℝ) / ((n.factorial : ℝ) - 1) =
      (((N.factorial / n.factorial + (N.factorial / n.factorial) / (n.factorial - 1) : ℕ) : ℤ) : ℝ) +
        (((N.factorial / n.factorial) % (n.factorial - 1) : ℕ) : ℝ) / ((n.factorial : ℝ) - 1) := by
    intro n hn
    rw [Finset.mem_Icc] at hn
    exact C_term_split N n hn.1 hn.2
  rw [Finset.sum_congr rfl hs, Finset.sum_add_distrib, ← Int.cast_sum, add_comm,
    Int.fract_add_intCast]

/-- The remainder r_n is just N! mod (n!−1), since n! ≡ 1. -/
theorem C_mod_eq (N n : ℕ) (hnN : n ≤ N) :
    (N.factorial / n.factorial) % (n.factorial - 1) = N.factorial % (n.factorial - 1) := by
  have hNm : N.factorial = n.factorial * (N.factorial / n.factorial) :=
    (Nat.mul_div_cancel' (Nat.factorial_dvd_factorial hnN)).symm
  obtain ⟨d, hd⟩ : ∃ d, n.factorial = d + 1 := ⟨n.factorial - 1, by have := Nat.factorial_pos n; omega⟩
  generalize N.factorial / n.factorial = m at hNm ⊢
  rw [hNm, hd, Nat.add_sub_cancel, add_mul, one_mul, Nat.mul_add_mod]

/-- fract(F_N) = fract(Σ_{n=2}^N (N! mod (n!−1))/(n!−1)). -/
theorem C_fract_mod' (N : ℕ) :
    Int.fract (∑ n ∈ Finset.Icc 2 N, (N.factorial : ℝ) / ((n.factorial : ℝ) - 1)) =
      Int.fract (∑ n ∈ Finset.Icc 2 N,
        ((N.factorial % (n.factorial - 1) : ℕ) : ℝ) / ((n.factorial : ℝ) - 1)) := by
  rw [C_fract_mod]
  congr 1
  apply Finset.sum_congr rfl
  intro n hn
  rw [Finset.mem_Icc] at hn
  rw [C_mod_eq N n hn.2]
