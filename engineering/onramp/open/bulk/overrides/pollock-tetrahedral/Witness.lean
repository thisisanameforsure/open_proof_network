/-! Non-vacuity witness (D-4 step 7): the statement's only binder is a natural number N, with no hypothesis; N = 0. -/

theorem witness : ∃ (N : ℕ), True := ⟨0, trivial⟩
