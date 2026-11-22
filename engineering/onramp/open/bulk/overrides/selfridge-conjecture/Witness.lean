/-! Non-vacuity witness (D-4 step 7): p = 3 satisfies the three Selfridge conditions (3 ≡ -2 mod 5, 2^2 ≡ 1 mod 3, F₄ = 3 ≡ 0 mod 3). -/

theorem witness : ∃ (p : ℕ), IsSelfridge p := ⟨3, by decide⟩
