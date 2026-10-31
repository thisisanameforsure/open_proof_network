import Mathlib

/-- (n+2)! - 1 is positive, as a real. -/
theorem B_den_pos (n : ℕ) : (0:ℝ) < ((n + 2).factorial - 1 : ℝ) := by
  have h : (2:ℕ) ≤ (n + 2).factorial := by
    have := Nat.factorial_le (show 2 ≤ n + 2 by omega)
    simpa using this
  have h' : (2:ℝ) ≤ ((n + 2).factorial : ℝ) := by exact_mod_cast h
  linarith

/-- Each term is at most 2/(n+2)!. -/
theorem B_term_le (n : ℕ) :
    1 / ((n + 2).factorial - 1 : ℝ) ≤ 2 / ((n + 2).factorial : ℝ) := by
  have h : (2:ℕ) ≤ (n + 2).factorial := by
    have := Nat.factorial_le (show 2 ≤ n + 2 by omega)
    simpa using this
  have h' : (2:ℝ) ≤ ((n + 2).factorial : ℝ) := by exact_mod_cast h
  rw [div_le_div_iff₀ (by linarith) (by linarith)]
  linarith

/-- The series of the problem is summable. -/
theorem B_summable :
    Summable (fun n : ℕ => 1 / ((n + 2).factorial - 1 : ℝ)) := by
  have hs : Summable (fun n : ℕ => 2 / ((n + 2).factorial : ℝ)) := by
    have := (Real.summable_pow_div_factorial 1)
    have h2 := (summable_nat_add_iff 2).mpr this
    simpa [div_eq_mul_inv] using h2.mul_left 2
  refine Summable.of_nonneg_of_le (fun n => ?_) (fun n => B_term_le n) hs
  exact le_of_lt (one_div_pos.mpr (B_den_pos n))

/-- Irrationality criterion: arbitrarily good nonzero integer approximations. -/
theorem B_irrational_of_approx (x : ℝ)
    (h : ∀ ε : ℝ, 0 < ε → ∃ a b : ℤ, 0 < |(b : ℝ) * x - a| ∧ |(b : ℝ) * x - a| < ε) :
    Irrational x := by
  rintro ⟨q, rfl⟩
  have hd : (0:ℝ) < q.den := by exact_mod_cast q.pos
  obtain ⟨a, b, h1, h2⟩ := h (1 / q.den) (by positivity)
  have key : (b : ℝ) * (q : ℝ) - a = ((b * q.num - a * q.den : ℤ) : ℝ) / q.den := by
    rw [eq_div_iff hd.ne']
    push_cast
    have : (q : ℝ) = q.num / q.den := by exact_mod_cast (Rat.num_div_den q).symm
    rw [this]; field_simp
  rw [key, abs_div, abs_of_pos hd] at h1 h2
  have hz : (b * q.num - a * q.den : ℤ) ≠ 0 := by
    intro hz; rw [hz] at h1; simp at h1
  have : (1:ℝ) ≤ |((b * q.num - a * q.den : ℤ) : ℝ)| := by
    rw [← Int.cast_abs]; exact_mod_cast Int.one_le_abs hz
  rw [div_lt_div_iff_of_pos_right hd] at h2
  linarith
