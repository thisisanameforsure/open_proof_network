import Mathlib

-- Pre-merge audit of route 2 (#1154, precheck 01M61FB49GCG51KBP68FYB6R7G): each have vs the printed closed_type

-- h1 -> erdos-68--h1
example : (∀ x : ℝ, (∀ M : ℕ, ∃ N : ℕ, M ≤ N ∧ ∀ m : ℤ, (N.factorial : ℝ) * x ≠ m) →
      Irrational x) ↔
    (∀ (x : ℝ), (∀ (M : ℕ), ∃ (N : ℕ), M ≤ N ∧ ∀ (m : ℤ), (↑N.factorial : ℝ) * x ≠ (↑m : ℝ)) → Irrational x) := Iff.rfl

-- h2 -> erdos-68--h5
example : (∀ N : ℕ, 4 ≤ N → ∃ c : ℝ, 1 / ((N : ℝ) + 1) < c ∧ c < 1 / N ∧
      (N.factorial : ℝ) * (∑' n : ℕ, 1 / ((n + 2).factorial - 1 : ℝ)) =
        (∑ n ∈ Finset.Icc 2 N, (N.factorial : ℝ) / ((n.factorial : ℝ) - 1)) + c) ↔
    (∀ (N : ℕ),
  (4 : ℕ) ≤ N →
    ∃ (c : ℝ),
      (1 : ℝ) / ((↑N : ℝ) + (1 : ℝ)) < c ∧
        c < (1 : ℝ) / (↑N : ℝ) ∧
          (↑N.factorial : ℝ) * ∑' (n : ℕ), (1 : ℝ) / ((↑(n + (2 : ℕ)).factorial : ℝ) - (1 : ℝ)) =
            ∑ n ∈ Finset.Icc (2 : ℕ) N, (↑N.factorial : ℝ) / ((↑n.factorial : ℝ) - (1 : ℝ)) + c) := Iff.rfl

-- h3 -> erdos-68--h6
example : (∀ M : ℕ, ∃ N : ℕ, M ≤ N ∧
      (Int.fract (∑ n ∈ Finset.Icc 2 N, (N.factorial : ℝ) / ((n.factorial : ℝ) - 1)) ≤ 1 - 1 / N ∨
        1 - 1 / ((N : ℝ) + 1) ≤
          Int.fract (∑ n ∈ Finset.Icc 2 N, (N.factorial : ℝ) / ((n.factorial : ℝ) - 1)))) ↔
    (∀ (M : ℕ),
  ∃ (N : ℕ),
    M ≤ N ∧
      (Int.fract (∑ n ∈ Finset.Icc (2 : ℕ) N, (↑N.factorial : ℝ) / ((↑n.factorial : ℝ) - (1 : ℝ))) ≤
          (1 : ℝ) - (1 : ℝ) / (↑N : ℝ) ∨
        (1 : ℝ) - (1 : ℝ) / ((↑N : ℝ) + (1 : ℝ)) ≤
          Int.fract (∑ n ∈ Finset.Icc (2 : ℕ) N, (↑N.factorial : ℝ) / ((↑n.factorial : ℝ) - (1 : ℝ))))) := Iff.rfl
