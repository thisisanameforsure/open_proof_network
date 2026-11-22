/-! Non-vacuity witness (D-4 step 7): a type of cardinality ℵ_ω (the cardinal's chosen representative) with, for each finite set, a chosen element outside it, which exists because the type is infinite. -/

theorem witness : ∃ (X : Type u) (f : Finset X → X), Cardinal.mk X = Cardinal.aleph Ordinal.omega0 ∧ ∀ (A : Finset X), f A ∉ A :=
  have hinf : Infinite (Cardinal.aleph Ordinal.omega0 : Cardinal.{u}).out :=
    Cardinal.infinite_iff.mpr (by rw [Cardinal.mk_out]; exact Cardinal.aleph0_le_aleph Ordinal.omega0)
  ⟨(Cardinal.aleph Ordinal.omega0 : Cardinal.{u}).out,
   fun A => Classical.choose (Infinite.exists_notMem_finset A),
   Cardinal.mk_out _,
   fun A => Classical.choose_spec (Infinite.exists_notMem_finset A)⟩
