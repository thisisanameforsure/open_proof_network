/-! Non-vacuity witness (D-4 step 7): n = 3, N = 5 < minModulus 3 = 6 and the three residues {0, 1, 2} in ZMod 5 satisfy every hypothesis before the conclusion. -/

theorem witness : ∃ (n : ℕ) (N : ℕ) (A : Finset (ZMod N)),
    (2 : ℕ) ≤ n ∧ (0 : ℕ) < N ∧ N < Arxiv.«2607.08366».minModulus n ∧ A.card = n :=
  ⟨3, 5, {0, 1, 2}, by norm_num, by norm_num, by decide, by decide⟩
