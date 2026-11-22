/-! Non-vacuity witness (D-4 step 7): n = 8 and k = 1, a run of one composite number (8 = 2 · 4). -/

theorem witness : ∃ (n : ℕ) (k : ℕ), (1 : ℕ) ≤ n ∧ (1 : ℕ) ≤ k ∧ ∀ (i : Fin k), (n + (↑i : ℕ)).Composite :=
  ⟨8, 1, by norm_num, le_refl 1, fun i => by
    rw [Fin.fin_one_eq_zero i]
    show Nat.Composite 8
    exact ⟨by norm_num, by norm_num⟩⟩
