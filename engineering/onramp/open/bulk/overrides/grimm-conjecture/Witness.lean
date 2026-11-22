/-! Non-vacuity witness (D-4 step 7): n = 4, k = 1: the single number 4 is composite. -/

theorem witness : ∃ (n k : ℕ), 1 ≤ n ∧ 1 ≤ k ∧ ∀ i : Fin k, (n + i).Composite :=
  ⟨4, 1, by norm_num, le_refl 1, fun i => by fin_cases i; decide⟩
