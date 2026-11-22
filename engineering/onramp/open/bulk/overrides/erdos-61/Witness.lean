/-! Non-vacuity witness (D-4 step 7): the one-vertex type `Fin 1` with its instances and the empty graph on it. -/

theorem witness : ∃ (α : Type u_1) (inst : Fintype α) (inst : DecidableEq α) (H : SimpleGraph α), True :=
  ⟨ULift (Fin 1), inferInstance, inferInstance, ⊥, trivial⟩
