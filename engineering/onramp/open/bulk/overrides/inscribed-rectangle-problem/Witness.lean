/-! Non-vacuity witness (D-4 step 7): the standard embedding of the unit circle into the Euclidean plane, z ↦ (Re z, Im z), which is continuous and injective from a compact space into a Hausdorff one, and r = 1. -/

theorem witness : ∃ (γ : Circle → EuclideanSpace ℝ (Fin 2)) (r : ℝ), Topology.IsEmbedding γ ∧ r > (0 : ℝ) :=
  ⟨fun z => (WithLp.equiv 2 (Fin 2 → ℝ)).symm ![(z : ℂ).re, (z : ℂ).im], 1,
    (Continuous.isClosedEmbedding
      (by fun_prop)
      (fun z w h => by
        have h' := congrArg (WithLp.equiv 2 (Fin 2 → ℝ)) h
        simp only [WithLp.equiv_symm_pk] at h'
        have h0 := congrFun h' 0
        have h1 := congrFun h' 1
        simp at h0 h1
        exact Subtype.ext (Complex.ext h0 h1))).isEmbedding,
    by norm_num⟩
