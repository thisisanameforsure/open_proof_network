/-! Non-vacuity witness (D-4 step 7): k = 1 with x = (1, 2) and y = (3): positive, disjoint, and 1 + 2 = 3. -/

theorem witness : ∃ (k n m : ℕ) (x : Fin n → ℕ) (y : Fin m → ℕ),
  (0 : ℕ) < n ∧ (0 : ℕ) < m ∧ (∀ (i : Fin n), (0 : ℕ) < x i) ∧ (∀ (j : Fin m), (0 : ℕ) < y j) ∧
    (∀ (i : Fin n) (j : Fin m), x i ≠ y j) ∧ ∑ i, x i ^ k = ∑ j, y j ^ k :=
  ⟨1, 2, 1, ![1, 2], ![3], by norm_num, by norm_num, by decide, by decide, by decide, by decide⟩
