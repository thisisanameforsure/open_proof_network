/-! Non-vacuity witness (D-4 step 7): n = 4, k = 1 and the zero vector, whose coordinates sum to 0. -/

theorem witness : ∃ (n k : ℕ) (x : Fin n → ℝ), 1 ≤ k ∧ 4 * k ≤ n ∧ ∑ i, x i = 0 :=
  ⟨4, 1, fun _ => 0, le_refl 1, by norm_num, by simp⟩
