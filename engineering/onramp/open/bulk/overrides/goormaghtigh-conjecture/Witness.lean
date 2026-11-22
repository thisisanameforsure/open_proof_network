/-! Non-vacuity witness (D-4 step 7): N = 31 = (2^5 - 1)/(2 - 1) = (5^3 - 1)/(5 - 1) is a Goormaghtigh number. (The statement's `IsGoormaghtighNumber` is not among the ported definitions, so this cannot be checked here.) -/

theorem witness : ∃ (N : ℕ), IsGoormaghtighNumber N := ⟨31, by decide⟩
