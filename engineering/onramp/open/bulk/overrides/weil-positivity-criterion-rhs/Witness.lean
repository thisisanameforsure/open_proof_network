/-! Non-vacuity witness (D-4 step 7): the zero compactly supported function is smooth and both of its weighted integrals vanish. -/

theorem witness : ∃ (g : CompactlySupportedContinuousMap ℝ ℝ),
    ContDiff ℝ ((⊤ : ℕ∞) : WithTop ℕ∞) ⇑g ∧ RiemannHypothesis.IsTestFunction ⇑g := by
  have h0 : (⇑(0 : CompactlySupportedContinuousMap ℝ ℝ)) = fun _ => (0 : ℝ) := rfl
  refine ⟨0, ?_, ?_⟩
  · rw [h0]; exact contDiff_const
  · unfold RiemannHypothesis.IsTestFunction
    simp [h0]
