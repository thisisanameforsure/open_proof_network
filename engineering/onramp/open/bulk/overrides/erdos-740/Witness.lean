/-! Non-vacuity witness (D-4 step 7): the complete graph on a countably infinite vertex type; every colouring of it is injective, so its chromatic cardinal is at least ℵ₀. -/

theorem witness : ∃ (V : Type u_1) (G : SimpleGraph V), Cardinal.aleph0 ≤ G.chromaticCardinal :=
  ⟨ULift.{u_1} ℕ, ⊤, le_csInf ⟨_, ULift.{u_1} ℕ, rfl, ⟨SimpleGraph.Hom.id⟩⟩ (by
    rintro κ ⟨C, rfl, ⟨c⟩⟩
    have h := Cardinal.mk_le_of_injective (SimpleGraph.Hom.injective_of_top_hom c)
    simpa using h)⟩
