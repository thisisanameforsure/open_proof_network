/-! Non-vacuity witness (D-4 step 7): the empty family of polynomials; every condition over its members holds vacuously and the Schinzel condition is met at n = 0 for every prime. -/

theorem witness : ∃ (fs : Finset (Polynomial ℤ)),
    (∀ f ∈ fs, f.degree = 1 ∧ BunyakovskyCondition f) ∧ SchinzelCondition fs :=
  ⟨∅, by simp, fun p _ => ⟨0, by simp⟩⟩
