/-! Non-vacuity witness (D-4 step 7): with n = 0 the free group on no generators is trivial, so the empty relator tuple normally generates it. -/

theorem witness : ∃ (n : ℕ) (r : RelatorTuple n), NormallyGenerates r :=
  ⟨0, Fin.elim0, Subsingleton.elim _ _⟩
