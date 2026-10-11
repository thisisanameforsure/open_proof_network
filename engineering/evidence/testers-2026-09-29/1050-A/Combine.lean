import Mathlib

/-- Step 4 of the annex: an odd multiple of p that is 2^a times an integer, and an integer
multiple M p, give M p = 2^a z. -/
theorem combine_two_adic_odd (p M : ℚ) (a : ℕ) (Ω A B m : ℤ) (hΩ : Odd Ω)
    (h1 : (Ω : ℚ) * p = 2 ^ a * A) (h2 : (B : ℚ) = M * p) (hm : (m : ℚ) = M) :
    ∃ z : ℤ, (z : ℚ) * 2 ^ a = M * p := by
  have hint : Ω * B = 2 ^ a * (m * A) := by
    have : ((Ω * B : ℤ) : ℚ) = ((2 ^ a * (m * A) : ℤ) : ℚ) := by
      push_cast
      rw [h2, ← hm]
      linear_combination (m : ℚ) * h1
    exact_mod_cast this
  obtain ⟨t, ht⟩ := hΩ
  have hcop : IsCoprime ((2 : ℤ) ^ a) Ω := by
    apply IsCoprime.pow_left
    exact ⟨-t, 1, by rw [ht]; ring⟩
  have hdvd : (2 : ℤ) ^ a ∣ B * Ω := ⟨m * A, by rw [mul_comm, hint]⟩
  obtain ⟨c, hc⟩ := hcop.dvd_of_dvd_mul_right hdvd
  refine ⟨c, ?_⟩
  rw [← h2, hc]
  push_cast
  ring
