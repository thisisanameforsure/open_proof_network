/-! Non-vacuity witness (D-4 step 7): the complete graph K₄ is cubic, and bridgeless because any edge vw is bypassed by the path v–x–w through a third vertex. -/

theorem witness : ∃ (V : Type) (inst : Fintype V) (inst : DecidableEq V) (G : SimpleGraph V) (inst : DecidableRel G.Adj),
    (∀ (v : V), G.degree v = (3 : ℕ)) ∧ G.IsBridgeless :=
  ⟨Fin 4, inferInstance, inferInstance, ⊤, inferInstance,
   fun v => by simp [SimpleGraph.complete_graph_degree],
   fun e he => by
    induction e using Sym2.inductionOn with
    | hf v w =>
      have hvw : v ≠ w := by simpa using he
      obtain ⟨x, hxv, hxw⟩ : ∃ x : Fin 4, x ≠ v ∧ x ≠ w := by revert v w; decide
      rintro ⟨-, hbr⟩
      exact hbr ⟨SimpleGraph.Walk.cons
        (by simp [SimpleGraph.sdiff_adj, SimpleGraph.fromEdgeSet_adj, Sym2.eq_iff, hxv, hxv.symm, hxw, hxw.symm, hvw, hvw.symm])
        (SimpleGraph.Walk.cons
          (by simp [SimpleGraph.sdiff_adj, SimpleGraph.fromEdgeSet_adj, Sym2.eq_iff, hxv, hxv.symm, hxw, hxw.symm, hvw, hvw.symm] : (⊤ \ SimpleGraph.fromEdgeSet {s(v, w)}).Adj x w)
          SimpleGraph.Walk.nil)⟩⟩
