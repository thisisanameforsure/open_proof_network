/-! Non-vacuity witness (D-4 step 7): N = 3 gives N(N+1)/2 = 6 = 3 + 3, which is even. -/

theorem witness : ∃ (N : ℕ), Even (N * (N + (1 : ℕ)) / (2 : ℕ)) := ⟨3, ⟨3, rfl⟩⟩
