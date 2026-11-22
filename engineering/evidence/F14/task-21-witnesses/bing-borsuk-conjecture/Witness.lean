/-! Non-vacuity witness (D-4 step 7): the one-point space `Unit` with n = 0 is metrizable, homogeneous (the identity moves its only point to itself), an absolute neighborhood retract (retract the whole ambient space onto the point) and of covering dimension exactly 0 (the cover `{univ}` refines every cover). -/

theorem witness : ∃ (n : ℕ) (X : Type) (inst : TopologicalSpace X),
  MetrizableSpace X ∧ HomogeneousSpace X ∧ IsAbsoluteNeighborhoodRetract X ∧ HasLebesgueCoveringDimensionEq X n := by
  refine ⟨0, Unit, inferInstance, inferInstance,
    ⟨fun x y => ⟨Homeomorph.refl Unit, Subsingleton.elim _ _⟩⟩,
    ⟨fun Y _ _ e _ => ⟨Set.univ, fun _ => (), isOpen_univ, Set.subset_univ _, continuousOn_const,
      fun x => Subsingleton.elim _ _⟩⟩, ?_, ?_⟩
  · intro 𝓤 _ _ hcov
    refine ⟨{Set.univ}, Set.finite_singleton _, by simp, by simp, ?_, ?_⟩
    · intro V hV
      rw [Set.mem_singleton_iff] at hV
      subst hV
      have hmem : (() : Unit) ∈ ⋃₀ 𝓤 := by rw [hcov]; trivial
      obtain ⟨U, hU, hxU⟩ := Set.mem_sUnion.mp hmem
      exact ⟨U, hU, fun x _ => by cases x; exact hxU⟩
    · intro x
      have h : {V ∈ ({Set.univ} : Set (Set Unit)) | x ∈ V} = {Set.univ} := by
        ext V; simp only [Set.mem_setOf_eq, Set.mem_singleton_iff, and_iff_left_iff_imp]; rintro rfl; trivial
      rw [h, Set.encard_singleton]; norm_num
  · intro m hm
    exact absurd hm (Nat.not_lt_zero m)
