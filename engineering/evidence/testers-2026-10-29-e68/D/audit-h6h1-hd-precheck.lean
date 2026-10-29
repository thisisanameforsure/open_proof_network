import Mathlib

-- Audit (D): B's partial on erdos-68--h6--h1 (hd skeleton), precheck 01M643VHA0A2A0614H4S65A08D.
-- ht: have ↔ printed
example : ( ∀ (N : ℕ), (4 : ℕ) ≤ N → ∃ (c : ℝ), (1 : ℝ) / ((↑N : ℝ) + (1 : ℝ)) < c ∧ c < (1 : ℝ) / (↑N : ℝ) ∧
      (↑N.factorial : ℝ) * ∑' (n : ℕ), (1 : ℝ) / ((↑(n + (2 : ℕ)).factorial : ℝ) - (1 : ℝ)) =
        ∑ n ∈ Finset.Icc (2 : ℕ) N, (↑N.factorial : ℝ) / ((↑n.factorial : ℝ) - (1 : ℝ)) + c ) ↔
  (∀ (N : ℕ),
  (4 : ℕ) ≤ N →
    ∃ (c : ℝ),
      (1 : ℝ) / ((↑N : ℝ) + (1 : ℝ)) < c ∧
        c < (1 : ℝ) / (↑N : ℝ) ∧
          (↑N.factorial : ℝ) * ∑' (n : ℕ), (1 : ℝ) / ((↑(n + (2 : ℕ)).factorial : ℝ) - (1 : ℝ)) =
            ∑ n ∈ Finset.Icc (2 : ℕ) N, (↑N.factorial : ℝ) / ((↑n.factorial : ℝ) - (1 : ℝ)) + c) := Iff.rfl
-- ht printed ↔ erdos-68--h5's Statement (lemma path)
example : (∀ (N : ℕ),
  (4 : ℕ) ≤ N →
    ∃ (c : ℝ),
      (1 : ℝ) / ((↑N : ℝ) + (1 : ℝ)) < c ∧
        c < (1 : ℝ) / (↑N : ℝ) ∧
          (↑N.factorial : ℝ) * ∑' (n : ℕ), (1 : ℝ) / ((↑(n + (2 : ℕ)).factorial : ℝ) - (1 : ℝ)) =
            ∑ n ∈ Finset.Icc (2 : ℕ) N, (↑N.factorial : ℝ) / ((↑n.factorial : ℝ) - (1 : ℝ)) + c) ↔
  ( ∀ (N : ℕ),
  (4 : ℕ) ≤ N →
    ∃ (c : ℝ),
      (1 : ℝ) / ((↑N : ℝ) + (1 : ℝ)) < c ∧
        c < (1 : ℝ) / (↑N : ℝ) ∧
          (↑N.factorial : ℝ) * ∑' (n : ℕ), (1 : ℝ) / ((↑(n + (2 : ℕ)).factorial : ℝ) - (1 : ℝ)) =
            ∑ n ∈ Finset.Icc (2 : ℕ) N, (↑N.factorial : ℝ) / ((↑n.factorial : ℝ) - (1 : ℝ)) + c ) := Iff.rfl
-- hd: have ↔ printed
example : ( ∀ (M : ℕ), ∃ (N : ℕ), M ≤ N ∧
      (2 : ℝ) / ((↑N : ℝ) + (1 : ℝ)) ≤
        Int.fract ((↑N.factorial : ℝ) * ∑' (n : ℕ), (1 : ℝ) / ((↑(n + (2 : ℕ)).factorial : ℝ) - (1 : ℝ))) ∧
      Int.fract ((↑N.factorial : ℝ) * ∑' (n : ℕ), (1 : ℝ) / ((↑(n + (2 : ℕ)).factorial : ℝ) - (1 : ℝ))) <
        (1 : ℝ) - (1 : ℝ) / ((↑N : ℝ) + (1 : ℝ)) ) ↔
  (∀ (M : ℕ),
  ∃ (N : ℕ),
    M ≤ N ∧
      (2 : ℝ) / ((↑N : ℝ) + (1 : ℝ)) ≤
          Int.fract ((↑N.factorial : ℝ) * ∑' (n : ℕ), (1 : ℝ) / ((↑(n + (2 : ℕ)).factorial : ℝ) - (1 : ℝ))) ∧
        Int.fract ((↑N.factorial : ℝ) * ∑' (n : ℕ), (1 : ℝ) / ((↑(n + (2 : ℕ)).factorial : ℝ) - (1 : ℝ))) <
          (1 : ℝ) - (1 : ℝ) / ((↑N : ℝ) + (1 : ℝ))) := Iff.rfl
