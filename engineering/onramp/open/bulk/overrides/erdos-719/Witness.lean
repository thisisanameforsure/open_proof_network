/-! Non-vacuity witness (D-4 step 7): r = 2 and the empty 2-uniform hypergraph on no vertices. -/

theorem witness : ∃ (r : ℕ) (n : ℕ) (H : Finset (Finset (Fin n))), (2 : ℕ) ≤ r ∧ H.IsUniform r :=
  ⟨2, 0, ∅, le_refl 2, fun e he => by simp at he⟩
