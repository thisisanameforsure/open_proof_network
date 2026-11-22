/-! Non-vacuity witness (D-4 step 7): the index type Fin 1, the zero diagonals and the identity unitaries. -/

theorem witness : ∃ (n : Type) (inst : Fintype n) (inst_1 : DecidableEq n) (d1 : n → ℂ) (d2 : n → ℂ) (U1 : ↥(unitary (Matrix n n ℂ))) (U2
  : ↥(unitary (Matrix n n ℂ))), True :=
  ⟨Fin 1, inferInstance, inferInstance, 0, 0, 1, 1, trivial⟩
