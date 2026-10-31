import Mathlib

-- Audit: each gate-written Statement.lean (graph main 55ae7cedcd) against the have in A's merged partial #1134.

-- h1
example : (∀ x : ℝ, (∀ M : ℕ, ∃ N : ℕ, M ≤ N ∧ ∀ m : ℤ, (N.factorial : ℝ) * x ≠ m) →
      Irrational x) ↔
    (∀ (x : ℝ), (∀ (M : ℕ), ∃ (N : ℕ), M ≤ N ∧ ∀ (m : ℤ), (↑N.factorial : ℝ) * x ≠ (↑m : ℝ)) → Irrational x) := Iff.rfl

-- h2
example : (∀ N : ℕ, 2 ≤ N → ∃ c : ℝ, 0 < c ∧ c ≤ 2 / N ∧
      (N.factorial : ℝ) * (∑' n : ℕ, 1 / ((n + 2).factorial - 1 : ℝ)) =
        (∑ n ∈ Finset.Icc 2 N, (N.factorial : ℝ) / ((n.factorial : ℝ) - 1)) + c) ↔
    (∀ (N : ℕ),
  (2 : ℕ) ≤ N →
    ∃ (c : ℝ),
      (0 : ℝ) < c ∧
        c ≤ (2 : ℝ) / (↑N : ℝ) ∧
          (↑N.factorial : ℝ) * ∑' (n : ℕ), (1 : ℝ) / ((↑(n + (2 : ℕ)).factorial : ℝ) - (1 : ℝ)) =
            ∑ n ∈ Finset.Icc (2 : ℕ) N, (↑N.factorial : ℝ) / ((↑n.factorial : ℝ) - (1 : ℝ)) + c) := Iff.rfl

-- h3
example : (∀ M : ℕ, ∃ N : ℕ, M ≤ N ∧
      Int.fract (∑ n ∈ Finset.Icc 2 N, (N.factorial : ℝ) / ((n.factorial : ℝ) - 1)) <
        1 - 2 / N) ↔
    (∀ (M : ℕ),
  ∃ (N : ℕ),
    M ≤ N ∧
      Int.fract (∑ n ∈ Finset.Icc (2 : ℕ) N, (↑N.factorial : ℝ) / ((↑n.factorial : ℝ) - (1 : ℝ))) <
        (1 : ℝ) - (2 : ℝ) / (↑N : ℝ)) := Iff.rfl
