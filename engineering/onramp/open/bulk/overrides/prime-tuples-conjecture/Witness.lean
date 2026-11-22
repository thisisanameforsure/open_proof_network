/-! Non-vacuity witness (D-4 step 7): k = 2 with a ≡ 1 and b ≡ 0: at n = 1 the product is 1, which no prime divides. -/

theorem witness : ∃ (k : ℕ) (a : Fin k → ℕ+) (b : Fin k → ℕ), (2 : ℕ) ≤ k ∧ ∀ p : ℕ, p.Prime → ∃ n : ℕ, ¬ p ∣ ∏ i, (a i * n + b i) := ⟨2, fun _ => 1, fun _ => 0, le_rfl, fun p hp => ⟨1, by simpa using hp.not_dvd_one⟩⟩
