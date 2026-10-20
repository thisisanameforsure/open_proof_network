lemma gramDet_divides_combined_det
    (r : ℕ) (hr : 0 < r)
    (b z w : Fin r → (Fin (2 * r) → ℤ))
    (h_orth : ∀ j k : Fin r, ∑ i, b j i * z k i = 0)
    (h_unimod : let Q : Matrix (Fin (2 * r)) (Fin (2 * r)) ℤ :=
        Matrix.of (fun i j =>
          if h : j.val < r then z ⟨j.val, h⟩ i
          else w ⟨j.val - r, by omega⟩ i)
      Q.det = 1 ∨ Q.det = -1) :
    (Matrix.det (Matrix.of (fun i j : Fin r => ∑ k, z i k * z j k))) ∣
    (Matrix.det (Matrix.of (fun i j : Fin (2 * r) =>
      if h : i.val < r then b ⟨i.val, h⟩ j
      else z ⟨i.val - r, by omega⟩ j))) := by
  obtain ⟨Q, hQ⟩ : ∃ Q : Matrix (Fin (2 * r)) (Fin (2 * r)) ℤ, (∀ i j : Fin (2 * r), Q i j = if h : j.val < r then (z (Fin.mk j.val h)) i else (w (Fin.mk (j.val - r) (by omega))) i) ∧ (Q.det = 1 ∨ Q.det = -1) := by
    exact ⟨ _, fun i j => rfl, h_unimod ⟩;
  set C : Matrix (Fin (2 * r)) (Fin (2 * r)) ℤ := Matrix.of (fun i j => if h : i.val < r then b (Fin.mk i.val h) j else z (Fin.mk (i.val - r) (by omega)) j);
  set BW : Matrix (Fin r) (Fin r) ℤ := Matrix.of (fun i j => ∑ k : Fin (2 * r), b i k * w j k) with hBW
  set ZZ : Matrix (Fin r) (Fin r) ℤ := Matrix.of (fun i j => ∑ k : Fin (2 * r), z i k * z j k) with hZZ
  set ZW : Matrix (Fin r) (Fin r) ℤ := Matrix.of (fun i j => ∑ k : Fin (2 * r), z i k * w j k) with hZW
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
  have hC_l : ∀ i k, C (e.symm (Sum.inl i)) k = b i k := by intro i k; rw [he_l]; simp [C]
  have hC_r : ∀ i k, C (e.symm (Sum.inr i)) k = z i k := by intro i k; rw [he_r]; simp [C]
  have hQ_l : ∀ j k, Q k (e.symm (Sum.inl j)) = z j k := by intro j k; rw [he_l, hQ.1]; simp
  have hQ_r : ∀ j k, Q k (e.symm (Sum.inr j)) = w j k := by intro j k; rw [he_r, hQ.1]; simp
  have key : (C * Q).submatrix e.symm e.symm = Matrix.fromBlocks 0 BW ZZ ZW := by
    ext (i | i) (j | j) <;>
      simp [Matrix.mul_apply, hC_l, hC_r, hQ_l, hQ_r, h_orth, hBW, hZZ, hZW]
  have h_det_CQ : (C * Q).det = (-1) ^ (r * r) * BW.det * ZZ.det := by
    rw [← Matrix.det_submatrix_equiv_self e.symm, key, det_block_zero_upper_left]
  have hdet : C.det * Q.det = (-1) ^ (r * r) * BW.det * ZZ.det := by
    rw [← Matrix.det_mul]; exact h_det_CQ
  show ZZ.det ∣ C.det
  rcases hQ.2 with h | h
  · rw [h] at hdet
    exact ⟨(-1) ^ (r * r) * BW.det, by linear_combination hdet⟩
  · rw [h] at hdet
    exact ⟨-((-1) ^ (r * r) * BW.det), by linear_combination -hdet⟩
