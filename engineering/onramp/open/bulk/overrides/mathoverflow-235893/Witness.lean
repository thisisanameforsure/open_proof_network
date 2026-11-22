/-! Non-vacuity witness (D-4 step 7): n = 2 and the identity self-equivalence of the plane, which maps connected sets to connected sets. -/

theorem witness : ∃ (n : ℕ) (f : ℝ^n ≃ ℝ^n), n > (1 : ℕ) ∧ IsConnectedMap f := ⟨2, Equiv.refl _, Nat.one_lt_two, fun s hs => by simpa using hs⟩
