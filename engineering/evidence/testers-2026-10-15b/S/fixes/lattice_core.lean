lemma lattice_core
    (r : ℕ) (hr : 2 ≤ r)
    (s : ℕ) (hs : s = 2 * r)
    (M : ℝ) (hM : (s : ℝ) - 1 ≤ M)
    (W : ℝ) (hW : 1 ≤ W)
    (u : Fin s → ℤ) (w : Fin s → ℕ)
    (hu_range : ∀ i, 0 ≤ u i ∧ (u i : ℝ) ≤ M)
    (hu_strict : StrictMono u)
    (hw_pos : ∀ i, 0 < w i)
    (hw_bound : ∀ i, (w i : ℝ) ≤ W) :
    ∃ a : Fin s → ℤ,
      (∀ (j : ℕ), j < r → ∑ i, (a i : ℝ) * (w i : ℝ) * ((u i : ℝ)) ^ j = 0) ∧
      (∑ i, (a i : ℝ) * (w i : ℝ) * ((u i : ℝ)) ^ r ≠ 0) ∧
      ((∑ i : Fin s, ((a i : ℤ) : ℝ) ^ 2) ^ r ≤
        (∏ j ∈ Finset.range r, ((M : ℝ) ^ j / (Nat.factorial j : ℝ))) ^ 4 *
        (2 : ℝ) ^ (r * (r - 1)) * (2 * (r : ℝ)) ^ r * W ^ (2 * r)) := by
  obtain ⟨v, hv_kernel, hv_indep, hv_mono, hv_prod, hv_succ⟩ :=
    successive_kernel_vectors_exist r hr s hs M W hW u w hu_range hu_strict hw_pos hw_bound
  obtain ⟨m, hm_nonzero, hm_bound⟩ :=
    excess_zero_with_comparison_bound r hr s hs M hM u w hu_range hu_strict hw_pos
      v hv_kernel hv_indep hv_mono hv_succ
  refine ⟨v m, fun j hj => hv_kernel m j hj, hm_nonzero, ?_⟩
  set P := ∏ j ∈ Finset.range r, ((M : ℝ) ^ j / (Nat.factorial j : ℝ))
  set Q := (2 : ℝ) ^ (r * (r - 1)) * (2 * (r : ℝ)) ^ r * W ^ (2 * r)
  calc (∑ i : Fin s, ((v m i : ℤ) : ℝ) ^ 2) ^ r
      ≤ P ^ 2 * ∏ k : Fin r, (∑ i : Fin s, ((v k i : ℤ) : ℝ) ^ 2) := hm_bound
    _ ≤ P ^ 2 * (Q * P ^ 2) := by
        gcongr
    _ = P ^ 4 * Q := by ring
    _ = P ^ 4 * (2 : ℝ) ^ (r * (r - 1)) * (2 * (r : ℝ)) ^ r * W ^ (2 * r) := by ring