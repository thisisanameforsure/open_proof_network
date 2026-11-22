/-! Non-vacuity witness (D-4 step 7): the one-term sequence [1] is a Barker sequence (every entry is ±1 and there are no off-peak autocorrelations). -/

theorem witness : ∃ (a : List ℤ), IsBarkerSequence a :=
  ⟨[1], by decide⟩
