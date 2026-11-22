/-! Non-vacuity witness (D-4 step 7): the complete graph on a vertex type of cardinality ℵ₁; it is coloured by its own vertices and every colouring of it is injective, so its chromatic cardinal is exactly ℵ₁. -/

theorem witness : ∃ (V : Type) (G : SimpleGraph V), G.chromaticCardinal = Cardinal.aleph 1 :=
  ⟨(Cardinal.aleph 1).out, ⊤, le_antisymm
    (csInf_le' ⟨(Cardinal.aleph 1).out, Cardinal.mk_out _, ⟨SimpleGraph.Hom.id⟩⟩)
    (le_csInf ⟨_, (Cardinal.aleph 1).out, Cardinal.mk_out _, ⟨SimpleGraph.Hom.id⟩⟩ (by
      rintro κ ⟨C, rfl, ⟨c⟩⟩
      exact (Cardinal.mk_out _).symm.le.trans
        (Cardinal.mk_le_of_injective (SimpleGraph.Hom.injective_of_top_hom c))))⟩
