/-! Non-vacuity witness (D-4 step 7): the whole real line is an infinite set. -/

theorem witness : ∃ (A : Set ℝ), A.Infinite :=
  ⟨Set.univ, Set.infinite_univ⟩
