lemma gramDet_orthogonal_factorization
    (r s : ℕ) (hs : s = 2 * r)
    (b z : Fin r → (Fin s → ℝ))
    (h_orth : ∀ j k : Fin r, ∑ i : Fin s, b j i * z k i = 0) :
    let C : Fin (2 * r) → (Fin s → ℝ) := fun idx =>
      if h : idx.val < r then b ⟨idx.val, h⟩ else z ⟨idx.val - r, by omega⟩
    Matrix.det (Matrix.of (fun i j : Fin (2 * r) => ∑ k : Fin s, C i k * C j k)) =
    Matrix.det (Matrix.of (fun i j : Fin r => ∑ k : Fin s, b i k * b j k)) *
    Matrix.det (Matrix.of (fun i j : Fin r => ∑ k : Fin s, z i k * z j k)) := by
  intro C
  let ψf : Fin (2 * r) → Fin r ⊕ Fin r := fun i =>
    if h : i.val < r then Sum.inl ⟨i.val, h⟩ else Sum.inr ⟨i.val - r, by omega⟩
  have hinj : Function.Injective ψf := by
    intro i j hij
    by_cases hi : i.val < r <;> by_cases hj : j.val < r <;> simp [ψf, hi, hj] at hij <;> ext <;> omega
  have hsurj : Function.Surjective ψf := by
    rintro (i | i)
    · exact ⟨⟨i.val, by omega⟩, by simp [ψf]⟩
    · refine ⟨⟨i.val + r, by omega⟩, ?_⟩
      simp [ψf]
  let e : Fin (2 * r) ≃ Fin r ⊕ Fin r := Equiv.ofBijective ψf ⟨hinj, hsurj⟩
  have he_l : ∀ i : Fin r, e.symm (Sum.inl i) = ⟨i.val, by omega⟩ := by
    intro i; rw [Equiv.symm_apply_eq]; show _ = ψf _; simp [ψf]
  have he_r : ∀ i : Fin r, e.symm (Sum.inr i) = ⟨i.val + r, by omega⟩ := by
    intro i; rw [Equiv.symm_apply_eq]; show _ = ψf _; simp [ψf]
  have hC_l : ∀ i : Fin r, C (e.symm (Sum.inl i)) = b i := by
    intro i; rw [he_l]; simp [C]
  have hC_r : ∀ i : Fin r, C (e.symm (Sum.inr i)) = z i := by
    intro i; rw [he_r]; simp [C]
  have key : (Matrix.of (fun i j : Fin (2 * r) => ∑ k : Fin s, C i k * C j k)).submatrix e.symm e.symm
      = Matrix.fromBlocks (Matrix.of (fun i j : Fin r => ∑ k : Fin s, b i k * b j k)) 0 0
          (Matrix.of (fun i j : Fin r => ∑ k : Fin s, z i k * z j k)) := by
    ext (i | i) (j | j)
    · simp [hC_l]
    · simp [hC_l, hC_r, h_orth]
    · simp only [Matrix.submatrix_apply, Matrix.of_apply, hC_l, hC_r, Matrix.fromBlocks_apply₂₁, Matrix.zero_apply]
      simpa only [mul_comm] using h_orth j i
    · simp [hC_r]
  rw [← Matrix.det_submatrix_equiv_self e.symm, key, Matrix.det_fromBlocks_zero₂₁]
