/-! Non-vacuity witness (D-4 step 7): the unit circle itself, sent into the Euclidean plane by the real-linear isometry ℂ ≃ ℝ² of the basis (1, i); continuous and injective from a compact space into a Hausdorff one, hence an embedding. -/

theorem witness : ∃ (γ : Circle → EuclideanSpace ℝ (Fin 2)), Topology.IsEmbedding γ :=
  ⟨fun z => Complex.orthonormalBasisOneI.repr (z : ℂ),
    (Continuous.isClosedEmbedding
      (Complex.orthonormalBasisOneI.repr.continuous.comp continuous_induced_dom)
      (fun a b h => Circle.ext (Complex.orthonormalBasisOneI.repr.injective h))).isEmbedding⟩
