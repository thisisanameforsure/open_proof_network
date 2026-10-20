lemma kernel_basis_product_bound
    (r : ℕ) (hr : 2 ≤ r)
    (s : ℕ) (hs : s = 2 * r)
    (M : ℝ)
    (W : ℝ) (hW : 1 ≤ W)
    (u : Fin s → ℤ) (w : Fin s → ℕ)
    (hu_range : ∀ i, 0 ≤ u i ∧ (u i : ℝ) ≤ M)
    (hu_strict : StrictMono u)
    (hw_pos : ∀ i, 0 < w i)
    (hw_bound : ∀ i, (w i : ℝ) ≤ W) :
    ∃ y : Fin r → (Fin s → ℤ),
      (∀ (k : Fin r) (j : ℕ), j < r →
        ∑ i, (y k i : ℝ) * (w i : ℝ) * ((u i : ℝ)) ^ j = 0) ∧
      (LinearIndependent ℝ (fun k : Fin r => (fun i : Fin s => ((y k i : ℤ) : ℝ)))) ∧
      (Monotone (fun k : Fin r => ∑ i : Fin s, ((y k i : ℤ) : ℝ) ^ 2)) ∧
      ∏ k : Fin r, (∑ i : Fin s, ((y k i : ℤ) : ℝ) ^ 2) ≤
        (2 : ℝ) ^ (r * (r - 1)) * (2 * (r : ℝ)) ^ r * W ^ (2 * r) *
        (∏ j ∈ Finset.range r, ((M : ℝ) ^ j / (Nat.factorial j : ℝ))) ^ 2 := by
  obtain ⟨y, hy_kernel, hy_indep, hy_mono, hy_prod⟩ :=
    annihilator_short_vectors r hr s hs u w (fun i => (hu_range i).1) hu_strict hw_pos
  refine ⟨y, hy_kernel, hy_indep, hy_mono, ?_⟩
  calc ∏ k : Fin r, (∑ i : Fin s, ((y k i : ℤ) : ℝ) ^ 2)
      ≤ (2 : ℝ) ^ (r * (r - 1)) *
        ∏ j ∈ Finset.range r,
          (∑ i : Fin s, ((w i : ℝ) * (Nat.choose (u i).toNat j : ℝ)) ^ 2) := hy_prod
    _ ≤ (2 : ℝ) ^ (r * (r - 1)) *
        ∏ j ∈ Finset.range r,
          ((s : ℝ) * W ^ 2 * ((M : ℝ) ^ j / (Nat.factorial j : ℝ)) ^ 2) := by
        gcongr with j hj
        exact norm_sq_defining_vector_bound s M W hW u w hu_range hw_bound j
    _ = (2 : ℝ) ^ (r * (r - 1)) * (2 * (r : ℝ)) ^ r * W ^ (2 * r) *
        (∏ j ∈ Finset.range r, ((M : ℝ) ^ j / (Nat.factorial j : ℝ))) ^ 2 := by
        rw [Finset.prod_mul_distrib, Finset.prod_mul_distrib]
        simp only [Finset.prod_const, Finset.card_range, Finset.prod_pow]
        rw [hs]; push_cast; ring