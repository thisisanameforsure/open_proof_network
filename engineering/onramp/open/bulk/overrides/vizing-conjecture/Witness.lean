/-! Non-vacuity witness (D-4 step 7): the one-vertex type with its finite and decidable-equality instances and the empty graph on it inhabit every leading binder. -/

theorem witness : ∃ (α β : Type) (_ : Fintype α) (_ : Fintype β) (_ : DecidableEq α) (_ : DecidableEq β) (_ : SimpleGraph α) (_ : SimpleGraph β), True := ⟨Fin 1, Fin 1, inferInstance, inferInstance, inferInstance, inferInstance, ⊥, ⊥, trivial⟩
