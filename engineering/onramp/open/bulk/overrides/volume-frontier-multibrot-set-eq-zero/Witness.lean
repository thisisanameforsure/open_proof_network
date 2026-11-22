/-! Non-vacuity witness (D-4 step 7): the degree n = 0 (the only leading binder carries no hypothesis). -/

theorem witness : ∃ (n : ℕ), True :=
  ⟨0, trivial⟩
