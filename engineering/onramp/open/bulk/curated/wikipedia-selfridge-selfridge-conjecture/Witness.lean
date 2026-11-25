/-! Non-vacuity witness (D-4 step 7): p = 3 satisfies the four Selfridge conditions: 3 is odd,
3 ≡ 3 (mod 5), 2^2 = 4 ≡ 1 (mod 3), and F₄ = 3 ≡ 0 (mod 3). -/

theorem witness : ∃ (p : ℕ), Selfridge.IsSelfridge p :=
  ⟨3, ⟨by decide, Or.inr (by decide), by decide, by decide +kernel⟩⟩
