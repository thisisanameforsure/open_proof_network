import Mathlib

theorem witness : ∃ (Qc : ℕ → ℕ → ℚ) (Qx : ℕ → ℚ) (Aq : ℕ → ℚ) (n : ℕ) (M : ℕ → ℕ) (C : ℕ → ℕ),
  (Qc = fun (n k : ℕ) =>
      ((-1 : ℚ) ^ k * (2 : ℚ) ^ (k * (k - (1 : ℕ)) / (2 : ℕ)) *
          ∏ i ∈ Finset.range k, ((2 : ℚ) ^ (n - i) - (1 : ℚ)) / ((2 : ℚ) ^ (i + (1 : ℕ)) - (1 : ℚ))) *
        ∏ i ∈ Finset.range n, ((2 : ℚ) ^ ((2 : ℕ) * n - k - i) - (1 : ℚ)) / ((2 : ℚ) ^ (i + (1 : ℕ)) - (1 : ℚ))) ∧
    (Qx = fun (n : ℕ) => ∑ k ∈ Finset.range (n + (1 : ℕ)), Qc n k * ((3 : ℚ) / (2 : ℚ) ^ n) ^ k) ∧
      (Aq = fun (n : ℕ) =>
          ∑ k ∈ Finset.range (n + (1 : ℕ)),
              (∑ j ∈ Finset.range (k + (1 : ℕ)), Qc n j / ((2 : ℚ) ^ (k - j) - (1 : ℚ))) * ((3 : ℚ) / (2 : ℚ) ^ n) ^ k +
            Qx n * ∑ j ∈ Finset.range n, (3 : ℚ) / ((2 : ℚ) ^ (j + (1 : ℕ)) - (3 : ℚ))) ∧
        (M = fun (n : ℕ) => ∏ m ∈ Finset.Ioc (n / (2 : ℕ)) n, ((2 : ℕ) ^ m - (1 : ℕ))) ∧
          (C = fun (n : ℕ) => ∏ j ∈ Finset.Ico (2 : ℕ) n, ((2 : ℕ) ^ (j + (1 : ℕ)) - (3 : ℕ))) ∧
            (∀ k ≤ n, ∃ (z : ℤ), (↑z : ℚ) * (2 : ℚ) ^ (k * (k - (1 : ℕ)) / (2 : ℕ)) = Qc n k) ∧
              ∀ k ≤ n,
                ∃ (z : ℤ),
                  (↑z : ℚ) * (2 : ℚ) ^ (k * (k - (1 : ℕ)) / (2 : ℕ)) =
                    (↑(M n) : ℚ) * ∑ j ∈ Finset.range (k + (1 : ℕ)), Qc n j / ((2 : ℚ) ^ (k - j) - (1 : ℚ)) :=
  ⟨_, _, _, 0, _, _, rfl, rfl, rfl, rfl, rfl, (by intro k hk; obtain rfl : k = 0 := (by omega); exact ⟨1, by simp⟩), (by intro k hk; obtain rfl : k = 0 := (by omega); exact ⟨0, by simp⟩)⟩
