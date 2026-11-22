/-! Non-vacuity witness (D-4 step 7): the empty graphs on one vertex have maximum degree 0, so (0+1)(0+1) = 1 ≤ 1 + 1. -/

theorem witness : ∃ (V : Type) (inst : Fintype V) (inst_1 : DecidableEq V) (G₁ : SimpleGraph V) (G₂ : SimpleGraph V) (inst_2 :
  DecidableRel G₁.Adj) (inst_3 : DecidableRel G₂.Adj),
  (G₁.maxDegree + (1 : ℕ)) * (G₂.maxDegree + (1 : ℕ)) ≤ Fintype.card V + (1 : ℕ) :=
  ⟨Fin 1, inferInstance, inferInstance, ⊥, ⊥, inferInstance, inferInstance, by decide⟩
