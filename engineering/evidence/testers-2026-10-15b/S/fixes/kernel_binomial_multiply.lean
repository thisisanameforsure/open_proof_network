lemma kernel_binomial_multiply
    (s : ℕ) (u : Fin s → ℤ) (w : Fin s → ℕ) (v : Fin s → ℤ)
    (hu_nonneg : ∀ i, 0 ≤ u i) (ℓ : ℕ) :
    ∀ n : ℕ, (∀ t : ℕ, t < n + ℓ → ∑ i, (v i : ℝ) * (w i : ℝ) * ((u i : ℝ)) ^ t = 0) →
    ∀ j : ℕ, j < n →
      ∑ i, ((Nat.choose (u i).toNat ℓ : ℤ) * v i : ℝ) * (w i : ℝ) * ((u i : ℝ)) ^ j = 0 := by
  intro n hn j hj
  induction' ℓ with ℓ ih generalizing n j;
  · aesop;
  · -- Use the identity: (ℓ+1) * choose(n, ℓ+1) = choose(n, ℓ) * (n - ℓ) for natural numbers.
    have h_identity : ∀ i, ((u i).toNat.choose (ℓ + 1) : ℝ) * (ℓ + 1) = ((u i).toNat.choose ℓ : ℝ) * ((u i : ℝ) - ℓ) := by
      intro i; norm_cast; have := Nat.choose_succ_right_eq ( Int.toNat ( u i ) ) ℓ; simp_all +decide [add_comm] ;
      by_cases h : ℓ ≤ Int.toNat ( u i ) <;> simp_all +decide [ Nat.choose_eq_zero_of_lt ];
    have h_sum_rewrite : ∑ i, ((u i).toNat.choose (ℓ + 1) : ℝ) * (v i : ℝ) * (w i : ℝ) * (u i : ℝ) ^ j * (ℓ + 1) = ∑ i, ((u i).toNat.choose ℓ : ℝ) * (v i : ℝ) * (w i : ℝ) * (u i : ℝ) ^ (j + 1) - ℓ * ∑ i, ((u i).toNat.choose ℓ : ℝ) * (v i : ℝ) * (w i : ℝ) * (u i : ℝ) ^ j := by
      rw [ Finset.mul_sum _ _ _ ] ; rw [ ← Finset.sum_sub_distrib ] ; congr ; ext i ; linear_combination' h_identity i * v i * w i * u i ^ j;
    simp_all +decide [ ← Finset.sum_mul _ _ _ ];
    exact eq_zero_of_ne_zero_of_mul_right_eq_zero ( by positivity ) ( h_sum_rewrite.trans ( by rw [ ih ( n + 1 ) ( fun t ht => hn t ( by linarith ) ) ( j + 1 ) ( by linarith ), ih n ( fun t ht => hn t ( by linarith ) ) j hj ] ; ring ) )