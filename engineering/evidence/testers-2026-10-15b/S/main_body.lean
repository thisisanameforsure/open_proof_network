  intro r hr N hN W hW δ hδ lam hlam D_r hDr D_r1 hDr1 f hf h1 h2 h3 S hS hS2 X hX N' hN' lam' hl1 hl2 D' hD' D1' hD1' g hg g1 g2 g3 S' hS' hS'2 hlt
  have hsilr : ∀ (r : ℕ), 1 ≤ r → ∀ (s : ℕ), s = 2 * r → ∀ (M : ℝ), (s : ℝ) - 1 ≤ M →
      ∀ (W : ℝ), 1 ≤ W → ∀ (u : Fin s → ℤ) (w : Fin s → ℕ),
      (∀ i, 0 ≤ u i ∧ (u i : ℝ) ≤ M) → StrictMono u → (∀ i, 0 < w i) → (∀ i, (w i : ℝ) ≤ W) →
      ∃ a : Fin s → ℤ,
        (∀ (j : ℕ), j < r → ∑ i, (a i : ℝ) * (w i : ℝ) * ((u i : ℝ)) ^ j = 0) ∧
        (∑ i, (a i : ℝ) * (w i : ℝ) * ((u i : ℝ)) ^ r ≠ 0) ∧
        (∀ i, |(a i : ℝ)| ≤ (256 * M / (r : ℝ)) ^ (r - 1 : ℕ) * W) := by
    sorry
  have hS'sub : ↑S' ⊆ ↑(intIcc N') := by
    intro u hu
    obtain ⟨a, b⟩ := hS' u hu
    simp only [intIcc, Finset.coe_Icc, Set.mem_Icc]
    exact ⟨a, b⟩
  have key := lambda_one_case r hr hsilr N' hN' W hW δ hδ D' hD' D1' hD1' g hg g1 g2 g3 S' hS'sub
    (fun u hu => hS'2 u hu)
  have hcmp := algebraic_comparison r hr D' D1' W δ hD' hD1' hW hδ 1 lam' one_pos
    (by simpa using hl1) (by norm_num; linarith)
  simp only [Nat.cast_one, one_pow, one_mul] at hcmp
  have hc6 : c₆ = 65536 := by
    unfold c₆ C₀_const B_const K_const c₉; norm_num
  rw [hc6] at hcmp
  have hr0 : (0 : ℝ) ≤ 2 * (r : ℝ) := by positivity
  have h2r : 2 * (r : ℝ) ≤ 2 * (r : ℝ) * lam' := by nlinarith
  nlinarith [mul_le_mul_of_nonneg_left hcmp hN'.le]
