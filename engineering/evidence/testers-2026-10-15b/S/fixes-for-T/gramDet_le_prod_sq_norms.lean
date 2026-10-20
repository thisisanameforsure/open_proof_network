lemma gramDet_le_prod_sq_norms (m s : ℕ) (v : Fin m → (Fin s → ℝ)) :
    gramDet m s v ≤ ∏ j : Fin m, ∑ k : Fin s, v j k ^ 2 := by
  set B : Matrix (Fin m) (Fin s) ℝ := Matrix.of (fun i j => v i j) with hB_def
  obtain ⟨U, hU⟩ : ∃ U : Matrix (Fin m) (Fin m) ℝ, U * U.transpose = B * B.transpose := by
    have h_pos_semidef : Matrix.PosSemidef (B * B.transpose) := by
      exact Matrix.posSemidef_conjTranspose_mul_self _
    letI : PartialOrder (Matrix (Fin m) (Fin m) ℝ) := Matrix.instPartialOrder
    letI : StarOrderedRing (Matrix (Fin m) (Fin m) ℝ) := Matrix.instStarOrderedRing
    letI : NonnegSpectrumClass ℝ (Matrix (Fin m) (Fin m) ℝ) := Matrix.instNonnegSpectrumClass
    have : 0 ≤ B * B.transpose := h_pos_semidef.nonneg
    obtain ⟨U, hU⟩ := CStarAlgebra.nonneg_iff_eq_star_mul_self.mp this
    use U.transpose
    simpa [Matrix.star_eq_conjTranspose, Matrix.conjTranspose_eq_transpose_of_trivial] using hU.symm
  convert hadamard_inequality m U using 1
  · have hG : gramDet m s v = (B * B.transpose).det := by
      unfold gramDet; congr 1
    rw [hG, ← hU, Matrix.det_mul, Matrix.det_transpose, sq]
  · simp_all +decide [← Matrix.ext_iff, Matrix.mul_apply, sq]