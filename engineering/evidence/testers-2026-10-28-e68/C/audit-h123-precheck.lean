import Mathlib

-- h1: partial's have (A/skel1-partial-v1.lean) vs the gate's printed closed_type (precheck 01M61A9S6RN8XYDXE2XGTA8326)
example : (∀ x : ℝ, (∀ M : ℕ, ∃ N : ℕ, M ≤ N ∧ ∀ m : ℤ, (N.factorial : ℝ) * x ≠ m) →
      Irrational x) ↔
    (∀ (x : ℝ), (∀ (M : ℕ), ∃ (N : ℕ), M ≤ N ∧ ∀ (m : ℤ), (↑N.factorial : ℝ) * x ≠ (↑m : ℝ)) → Irrational x) := Iff.rfl

-- h1: the printed type also reads back on its own (round trip)
example : (∀ (x : ℝ), (∀ (M : ℕ), ∃ (N : ℕ), M ≤ N ∧ ∀ (m : ℤ), (↑N.factorial : ℝ) * x ≠ (↑m : ℝ)) → Irrational x) → (∀ x : ℝ, (∀ M : ℕ, ∃ N : ℕ, M ≤ N ∧ ∀ m : ℤ, (N.factorial : ℝ) * x ≠ m) →
      Irrational x) := id

-- h2: partial's have (A/skel1-partial-v1.lean) vs the gate's printed closed_type (precheck 01M61A9S6RN8XYDXE2XGTA8326)
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

-- h2: the printed type also reads back on its own (round trip)
example : (∀ (N : ℕ),
  (2 : ℕ) ≤ N →
    ∃ (c : ℝ),
      (0 : ℝ) < c ∧
        c ≤ (2 : ℝ) / (↑N : ℝ) ∧
          (↑N.factorial : ℝ) * ∑' (n : ℕ), (1 : ℝ) / ((↑(n + (2 : ℕ)).factorial : ℝ) - (1 : ℝ)) =
            ∑ n ∈ Finset.Icc (2 : ℕ) N, (↑N.factorial : ℝ) / ((↑n.factorial : ℝ) - (1 : ℝ)) + c) → (∀ N : ℕ, 2 ≤ N → ∃ c : ℝ, 0 < c ∧ c ≤ 2 / N ∧
      (N.factorial : ℝ) * (∑' n : ℕ, 1 / ((n + 2).factorial - 1 : ℝ)) =
        (∑ n ∈ Finset.Icc 2 N, (N.factorial : ℝ) / ((n.factorial : ℝ) - 1)) + c) := id

-- h3: partial's have (A/skel1-partial-v1.lean) vs the gate's printed closed_type (precheck 01M61A9S6RN8XYDXE2XGTA8326)
example : (∀ M : ℕ, ∃ N : ℕ, M ≤ N ∧
      Int.fract (∑ n ∈ Finset.Icc 2 N, (N.factorial : ℝ) / ((n.factorial : ℝ) - 1)) <
        1 - 2 / N) ↔
    (∀ (M : ℕ),
  ∃ (N : ℕ),
    M ≤ N ∧
      Int.fract (∑ n ∈ Finset.Icc (2 : ℕ) N, (↑N.factorial : ℝ) / ((↑n.factorial : ℝ) - (1 : ℝ))) <
        (1 : ℝ) - (2 : ℝ) / (↑N : ℝ)) := Iff.rfl

-- h3: the printed type also reads back on its own (round trip)
example : (∀ (M : ℕ),
  ∃ (N : ℕ),
    M ≤ N ∧
      Int.fract (∑ n ∈ Finset.Icc (2 : ℕ) N, (↑N.factorial : ℝ) / ((↑n.factorial : ℝ) - (1 : ℝ))) <
        (1 : ℝ) - (2 : ℝ) / (↑N : ℝ)) → (∀ M : ℕ, ∃ N : ℕ, M ≤ N ∧
      Int.fract (∑ n ∈ Finset.Icc 2 N, (N.factorial : ℝ) / ((n.factorial : ℝ) - 1)) <
        1 - 2 / N) := id
