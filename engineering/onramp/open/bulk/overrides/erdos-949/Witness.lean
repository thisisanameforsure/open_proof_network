/-! Non-vacuity witness (D-4 step 7): the empty set of reals is sum-free. -/

theorem witness : ∃ (S : Set ℝ), ∀ a ∈ S, ∀ b ∈ S, a + b ∉ S := ⟨∅, by simp⟩
