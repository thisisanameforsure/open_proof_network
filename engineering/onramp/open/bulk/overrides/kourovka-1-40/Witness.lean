/-! Non-vacuity witness (D-4 step 7): the trivial group with H = K = ⊤, both normal and Engel (every commutator is 1), and ⊤ ⊔ ⊤ = ⊤. -/

theorem witness : ∃ (G : Type) (inst : Group G) (H K : Subgroup G),
    H.Normal ∧ K.Normal ∧ Kourovka.«1.40».IsEngelGroup H ∧ Kourovka.«1.40».IsEngelGroup K ∧ H ⊔ K = ⊤ :=
  ⟨Unit, inferInstance, ⊤, ⊤, inferInstance, inferInstance,
   fun _ _ => ⟨0, Subsingleton.elim _ _⟩, fun _ _ => ⟨0, Subsingleton.elim _ _⟩, by simp⟩
