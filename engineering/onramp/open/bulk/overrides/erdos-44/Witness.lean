/-! Non-vacuity witness (D-4 step 7): N = 1, the empty subset of {1} (Sidon vacuously) and ε = 1. -/

theorem witness : ∃ (N : ℕ) (A : Finset ℕ) (ε : ℝ), N ≥ (1 : ℕ) ∧ A ⊆ Finset.Icc 1 N ∧ IsSidon (A : Set ℕ) ∧ ε > (0 : ℝ) := ⟨1, ∅, 1, le_rfl, Finset.empty_subset _, by simp [IsSidon], by norm_num⟩
