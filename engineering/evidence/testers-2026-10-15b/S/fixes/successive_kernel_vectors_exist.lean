lemma successive_kernel_vectors_exist
    (r : ℕ) (hr : 2 ≤ r)
    (s : ℕ) (hs : s = 2 * r)
    (M : ℝ)
    (W : ℝ) (hW : 1 ≤ W)
    (u : Fin s → ℤ) (w : Fin s → ℕ)
    (hu_range : ∀ i, 0 ≤ u i ∧ (u i : ℝ) ≤ M)
    (hu_strict : StrictMono u)
    (hw_pos : ∀ i, 0 < w i)
    (hw_bound : ∀ i, (w i : ℝ) ≤ W) :
    ∃ v : Fin r → (Fin s → ℤ),
      (∀ (k : Fin r) (j : ℕ), j < r →
        ∑ i, (v k i : ℝ) * (w i : ℝ) * ((u i : ℝ)) ^ j = 0) ∧
      (LinearIndependent ℝ (fun k : Fin r => (fun i : Fin s => ((v k i : ℤ) : ℝ)))) ∧
      (Monotone (fun k : Fin r => ∑ i : Fin s, ((v k i : ℤ) : ℝ) ^ 2)) ∧
      (∏ k : Fin r, (∑ i : Fin s, ((v k i : ℤ) : ℝ) ^ 2) ≤
        (2 : ℝ) ^ (r * (r - 1)) * (2 * (r : ℝ)) ^ r * W ^ (2 * r) *
        (∏ j ∈ Finset.range r, ((M : ℝ) ^ j / (Nat.factorial j : ℝ))) ^ 2) ∧
      (∀ k : Fin r, ∀ x : Fin s → ℤ,
        (∀ j : ℕ, j < r → ∑ i, (x i : ℝ) * (w i : ℝ) * ((u i : ℝ)) ^ j = 0) →
        (fun i : Fin s => (x i : ℝ)) ∉
          Submodule.span ℝ ((fun j : Fin r => fun i : Fin s => (v j i : ℝ)) ''
            { j | j.val < k.val }) →
        ∑ i : Fin s, ((v k i : ℤ) : ℝ) ^ 2 ≤ ∑ i : Fin s, ((x i : ℤ) : ℝ) ^ 2) := by
  obtain ⟨ v, hv₁, hv₂, hv₃, hv₄ ⟩ := successive_minima_in_kernel r hr s hs u w hu_strict hw_pos;
  refine' ⟨ v, hv₁, hv₂, hv₃, _, hv₄ ⟩;
  convert successive_minima_product_bound r hr s hs M W hW u w hu_range hu_strict hw_pos hw_bound v hv₄ using 1 <;> (try (first | with_reducible_and_instances rfl | (show (_ : LE ℝ) = _; rfl) | (show (_ : LT ℝ) = _; rfl) | (show (_ : LE ℝ) = _; with_unfolding_all rfl) | (show (_ : LT ℝ) = _; with_unfolding_all rfl)))