/-! Non-vacuity witness (D-4 step 7): n = 6 with A = {1, …, 6} (six elements, more than 6/2 + 6/3 − 6/6 = 4) and the odd length l = 3 ≤ 6/3 + 1. -/

theorem witness : ∃ (n : ℕ) (A : Finset ℕ) (l : ℕ),
  A ⊆ Finset.Icc (1 : ℕ) n ∧
    n / (2 : ℕ) + n / (3 : ℕ) - n / (6 : ℕ) < A.card ∧ Odd l ∧ (3 : ℕ) ≤ l ∧ l ≤ n / (3 : ℕ) + (1 : ℕ) :=
  ⟨6, Finset.Icc 1 6, 3, Finset.Subset.refl _, by simp, ⟨1, rfl⟩, by norm_num, by norm_num⟩
