/-! Non-vacuity witness (D-4 step 7): r = 0 (the only leading binder carries no hypothesis). -/

theorem witness : ∃ (r : ℕ), True :=
  ⟨0, trivial⟩
