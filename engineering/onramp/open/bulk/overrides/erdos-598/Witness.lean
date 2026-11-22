/-! Non-vacuity witness (D-4 step 7): the cardinal 0 and the infinite type ULift ℕ. -/

theorem witness : ∃ (κ : Cardinal.{u_1}) (m : Type u_1), Infinite m :=
  ⟨0, ULift ℕ, inferInstance⟩
