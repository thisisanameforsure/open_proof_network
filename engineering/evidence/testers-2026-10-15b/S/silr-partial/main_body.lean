  have hskv : ∀ (r : ℕ), 2 ≤ r → ∀ (s : ℕ), s = 2 * r → ∀ (M : ℝ) (W : ℝ), 1 ≤ W →
      ∀ (u : Fin s → ℤ) (w : Fin s → ℕ), (∀ i, 0 ≤ u i ∧ (u i : ℝ) ≤ M) → StrictMono u →
      (∀ i, 0 < w i) → (∀ i, (w i : ℝ) ≤ W) →
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
    sorry
  intro r hr s hs M hM W hW u w h1 h2 h3 h4
  exact small_integer_linear_relation_proof r hr hskv s hs M hM W hW u w h1 h2 h3 h4
