/-! Non-vacuity witness (D-4 step 7): the one-element list [0] is not empty. -/

theorem witness : ∃ (S₀ : List ℤ), S₀ ≠ [] := ⟨[0], List.cons_ne_nil 0 []⟩
