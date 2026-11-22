/-! Non-vacuity witness (D-4 step 7): the two-point set {(0,0), (1,1)} has two elements. -/

theorem witness : ∃ (X : Finset (ℝ × ℝ)), (2 : ℕ) ≤ Finset.card X :=
  ⟨{((0 : ℝ), (0 : ℝ)), (1, 1)}, (Finset.card_pair (by simp)).ge⟩
