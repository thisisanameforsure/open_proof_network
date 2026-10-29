import Mathlib

-- A1 hcore: the partial's `have` (A/partial-h3-A1.lean) vs precheck 01M6422N00JZK93P757RF6FJ17's closed_type
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

-- B-4 h1: B/partial-h6-route3.lean's `have` vs precheck 01M64264AGV6E9DBS1TYP8Q3KE's closed_type
example : (∀ M : ℕ, ∃ N : ℕ, M ≤ N ∧
      Int.fract (∑ n ∈ Finset.Icc (2 : ℕ) N, (↑N.factorial : ℝ) / ((↑n.factorial : ℝ) - (1 : ℝ))) ≤ (1 : ℝ) - (1 : ℝ) / (↑N : ℝ)) ↔
    (∀ (M : ℕ),
  ∃ (N : ℕ),
    M ≤ N ∧
      Int.fract (∑ n ∈ Finset.Icc (2 : ℕ) N, (↑N.factorial : ℝ) / ((↑n.factorial : ℝ) - (1 : ℝ))) ≤
        (1 : ℝ) - (1 : ℝ) / (↑N : ℝ)) := Iff.rfl

-- A1 hcore is the statement about N!·S with S the root's sum (same series as Opn.erdos_68)
example : (∑' n : ℕ, 1 / ((n + 2).factorial - 1 : ℝ)) =
    ∑' (n : ℕ), (1 : ℝ) / ((↑(n + (2 : ℕ)).factorial : ℝ) - (1 : ℝ)) := by push_cast; rfl
