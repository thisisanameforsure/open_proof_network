import Mathlib

theorem witness : ∃ (Qc : ℕ → ℕ → ℚ) (n : ℕ) (k : ℕ),
      (Qc = fun (n k : ℕ) =>
          ((-1 : ℚ) ^ k * (2 : ℚ) ^ (k * (k - (1 : ℕ)) / (2 : ℕ)) *
              ∏ i ∈ Finset.range k, ((2 : ℚ) ^ (n - i) - (1 : ℚ)) / ((2 : ℚ) ^ (i + (1 : ℕ)) - (1 : ℚ))) *
            ∏ i ∈ Finset.range n, ((2 : ℚ) ^ ((2 : ℕ) * n - k - i) - (1 : ℚ)) / ((2 : ℚ) ^ (i + (1 : ℕ)) - (1 : ℚ))) ∧
        (∀ k ≤ n, ∃ (z : ℤ), (↑z : ℚ) * (2 : ℚ) ^ (k * (k - (1 : ℕ)) / (2 : ℕ)) = Qc n k) ∧ k ≤ n := by
  refine ⟨_, 0, 0, rfl, ?_, le_refl 0⟩
  intro k hk
  obtain rfl : k = 0 := by omega
  exact ⟨1, by simp⟩
