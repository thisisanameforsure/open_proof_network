/-! Non-vacuity witness (D-4 step 7): n = 1 is positive. (Unverified: the statement's notation `ℓ(·)` is not defined by any ported module, so the statement does not elaborate.) -/

theorem witness : ∃ (n : ℕ), 0 < n := ⟨1, Nat.one_pos⟩
