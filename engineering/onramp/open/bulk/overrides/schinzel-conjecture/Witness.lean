/-! Non-vacuity witness (D-4 step 7): the empty family of polynomials; the Bunyakovsky condition is vacuous and the empty product 1 has no fixed prime divisor. -/

theorem witness : ∃ (fs : Finset ℤ[X]), (∀ f ∈ fs, BunyakovskyCondition f) ∧ SchinzelCondition fs :=
  ⟨∅, fun _ h => absurd h (Finset.notMem_empty _), by simp [SchinzelCondition]⟩
