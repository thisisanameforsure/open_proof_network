import Mathlib

-- Audit (D): A's partial #1176 on erdos-68--h3, precheck 01M6422N00JZK93P757RF6FJ17, graph 4f771bb8ad.
-- ht: have ↔ printed closed_type
example : (∀ (N : ℕ), (2 : ℕ) ≤ N → ∃ (c : ℝ), (0 : ℝ) < c ∧ c ≤ (2 : ℝ) / (↑N : ℝ) ∧
      (↑N.factorial : ℝ) * ∑' (n : ℕ), (1 : ℝ) / ((↑(n + (2 : ℕ)).factorial : ℝ) - (1 : ℝ)) =
        ∑ n ∈ Finset.Icc (2 : ℕ) N, (↑N.factorial : ℝ) / ((↑n.factorial : ℝ) - (1 : ℝ)) + c) ↔
  (∀ (N : ℕ),
  (2 : ℕ) ≤ N →
    ∃ (c : ℝ),
      (0 : ℝ) < c ∧
        c ≤ (2 : ℝ) / (↑N : ℝ) ∧
          (↑N.factorial : ℝ) * ∑' (n : ℕ), (1 : ℝ) / ((↑(n + (2 : ℕ)).factorial : ℝ) - (1 : ℝ)) =
            ∑ n ∈ Finset.Icc (2 : ℕ) N, (↑N.factorial : ℝ) / ((↑n.factorial : ℝ) - (1 : ℝ)) + c) := Iff.rfl
-- ht: printed closed_type ↔ erdos-68--h2's Statement (the restatement it should become a lemma of)
example : (∀ (N : ℕ),
  (2 : ℕ) ≤ N →
    ∃ (c : ℝ),
      (0 : ℝ) < c ∧
        c ≤ (2 : ℝ) / (↑N : ℝ) ∧
          (↑N.factorial : ℝ) * ∑' (n : ℕ), (1 : ℝ) / ((↑(n + (2 : ℕ)).factorial : ℝ) - (1 : ℝ)) =
            ∑ n ∈ Finset.Icc (2 : ℕ) N, (↑N.factorial : ℝ) / ((↑n.factorial : ℝ) - (1 : ℝ)) + c) ↔
  ( ∀ (N : ℕ),
  (2 : ℕ) ≤ N →
    ∃ (c : ℝ),
      (0 : ℝ) < c ∧
        c ≤ (2 : ℝ) / (↑N : ℝ) ∧
          (↑N.factorial : ℝ) * ∑' (n : ℕ), (1 : ℝ) / ((↑(n + (2 : ℕ)).factorial : ℝ) - (1 : ℝ)) =
            ∑ n ∈ Finset.Icc (2 : ℕ) N, (↑N.factorial : ℝ) / ((↑n.factorial : ℝ) - (1 : ℝ)) + c ) := Iff.rfl
-- hcore: have ↔ printed closed_type
example : (∃ δ : ℝ, 0 < δ ∧ ∀ M : ℕ, ∃ N : ℕ, M ≤ N ∧
      δ ≤ Int.fract ((N.factorial : ℝ) * ∑' n : ℕ, (1 : ℝ) / (((n + 2).factorial : ℝ) - 1)) ∧
      Int.fract ((N.factorial : ℝ) * ∑' n : ℕ, (1 : ℝ) / (((n + 2).factorial : ℝ) - 1)) ≤ 1 - δ) ↔
  (∃ (δ : ℝ),
  (0 : ℝ) < δ ∧
    ∀ (M : ℕ),
      ∃ (N : ℕ),
        M ≤ N ∧
          δ ≤ Int.fract ((↑N.factorial : ℝ) * ∑' (n : ℕ), (1 : ℝ) / ((↑(n + (2 : ℕ)).factorial : ℝ) - (1 : ℝ))) ∧
            Int.fract ((↑N.factorial : ℝ) * ∑' (n : ℕ), (1 : ℝ) / ((↑(n + (2 : ℕ)).factorial : ℝ) - (1 : ℝ))) ≤
              (1 : ℝ) - δ) := Iff.rfl
-- hcore's sum is the root's sum S (the root's own spelling)
example : (∑' (n : ℕ), (1 : ℝ) / ((↑(n + (2 : ℕ)).factorial : ℝ) - (1 : ℝ))) = ∑' n : ℕ, 1 / ((n + 2).factorial - 1 : ℝ) := rfl
