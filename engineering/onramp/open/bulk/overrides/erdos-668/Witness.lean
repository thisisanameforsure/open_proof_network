/-! Non-vacuity witness (D-4 step 7): the number of sets m = 0 (the only leading binder carries no hypothesis). -/

theorem witness : ∃ (m : ℕ), True :=
  ⟨0, trivial⟩
