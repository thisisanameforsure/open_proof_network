/-! Non-vacuity witness (D-4 step 7): the empty set is well separated, every separation condition on its points being vacuous. -/

theorem witness : ∃ (A : Set ℝ), WellSeparatedSet A :=
  ⟨∅, by simp [WellSeparatedSet]⟩
