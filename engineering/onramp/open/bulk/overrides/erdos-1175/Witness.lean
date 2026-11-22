/-! Non-vacuity witness (D-4 step 7): the continuum is an uncountable cardinal. -/

theorem witness : ∃ (κ : Cardinal), Cardinal.aleph0 < κ :=
  ⟨Cardinal.continuum, Cardinal.aleph0_lt_continuum⟩
