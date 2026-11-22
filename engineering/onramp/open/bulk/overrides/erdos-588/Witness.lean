/-! Non-vacuity witness (D-4 step 7): k = 4 satisfies 4 ≤ k. -/

theorem witness : ∃ (k : ℕ), (4 : ℕ) ≤ k :=
  ⟨4, le_refl 4⟩
