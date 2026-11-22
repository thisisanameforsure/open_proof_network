/-! Non-vacuity witness (D-4 step 7): S₃ itself is a nontrivial finite group whose conjugacy classes have distinct sizes (1, 2, 3). (Written unchecked; `HasDistinctConjClassSizes` is not defined by any ported module.) -/

theorem witness : ∃ (G : Type) (_ : Group G) (_ : Fintype G) (_ : Nontrivial G),
    HasDistinctConjClassSizes (G := G) :=
  ⟨Equiv.Perm (Fin 3), inferInstance, inferInstance, inferInstance, by decide⟩
