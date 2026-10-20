import Mathlib

open scoped Nat

theorem witness : ∃ (r : ℕ) (s : ℕ) (M : ℝ) (W : ℝ) (u : Fin s → ℤ) (w : Fin s → ℕ),
    (1 : ℕ) ≤ r ∧ s = (2 : ℕ) * r ∧ (↑s : ℝ) - (1 : ℝ) ≤ M ∧ (1 : ℝ) ≤ W ∧
      (∀ (i : Fin s), (0 : ℤ) ≤ u i ∧ (↑(u i) : ℝ) ≤ M) ∧ StrictMono u ∧ (∀ (i : Fin s), (0 : ℕ) < w i) ∧
        ∀ (i : Fin s), (↑(w i) : ℝ) ≤ W := by
  refine ⟨1, 2, 1, 1, ![0, 1], ![1, 1], le_rfl, rfl, by norm_num, le_rfl, ?_, ?_, ?_, ?_⟩
  · intro i; fin_cases i <;> simp
  · intro i j hij
    fin_cases i <;> fin_cases j <;> simp_all
  · intro i; fin_cases i <;> simp
  · intro i; fin_cases i <;> simp
