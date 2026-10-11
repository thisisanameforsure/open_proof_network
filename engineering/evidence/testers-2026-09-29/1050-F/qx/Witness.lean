import Mathlib

theorem witness : ∃ (Qc : ℕ → ℕ → ℚ) (Qx : ℕ → ℚ) (n : ℕ),
    (Qc = fun (n k : ℕ) =>
      ((-1 : ℚ) ^ k * (2 : ℚ) ^ (k * (k - 1) / 2) *
          ∏ i ∈ Finset.range k, ((2 : ℚ) ^ (n - i) - 1) / ((2 : ℚ) ^ (i + 1) - 1)) *
        ∏ i ∈ Finset.range n, ((2 : ℚ) ^ (2 * n - k - i) - 1) / ((2 : ℚ) ^ (i + 1) - 1)) ∧
      Qx = fun (n : ℕ) => ∑ k ∈ Finset.range (n + 1), Qc n k * ((3 : ℚ) / (2 : ℚ) ^ n) ^ k :=
  ⟨_, _, 0, rfl, rfl⟩
