import Mathlib

theorem witness : ∃ (Qc : ℕ → ℕ → ℚ) (n k : ℕ),
    (Qc = fun (n k : ℕ) =>
      ((-1 : ℚ) ^ k * (2 : ℚ) ^ (k * (k - 1) / 2) *
          ∏ i ∈ Finset.range k, ((2 : ℚ) ^ (n - i) - 1) / ((2 : ℚ) ^ (i + 1) - 1)) *
        ∏ i ∈ Finset.range n, ((2 : ℚ) ^ (2 * n - k - i) - 1) / ((2 : ℚ) ^ (i + 1) - 1)) ∧ k ≤ n :=
  ⟨_, 0, 0, rfl, le_refl 0⟩
