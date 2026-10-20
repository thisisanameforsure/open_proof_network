lemma norm_sq_defining_vector_bound
    (s : ℕ) (M : ℝ) (W : ℝ) (hW : 1 ≤ W)
    (u : Fin s → ℤ) (w : Fin s → ℕ)
    (hu_range : ∀ i, 0 ≤ u i ∧ (u i : ℝ) ≤ M)
    (hw_bound : ∀ i, (w i : ℝ) ≤ W)
    (j : ℕ) :
    ∑ i : Fin s, ((w i : ℝ) * (Nat.choose (u i).toNat j : ℝ)) ^ 2 ≤
      (s : ℝ) * W ^ 2 * ((M : ℝ) ^ j / (Nat.factorial j : ℝ)) ^ 2 := by
  have h_term_bound : ∀ i : Fin s, ((w i : ℝ) * Nat.choose (u i).toNat j) ^ 2 ≤ (W * (M ^ j / (Nat.factorial j))) ^ 2 := by
    have h_binom_bound : ∀ i : Fin s, (Nat.choose (u i).toNat j : ℝ) ≤ (M ^ j / (Nat.factorial j)) := by
      intro i
      have h_choose_bound : (Nat.choose (u i).toNat j : ℝ) ≤ (u i).toNat ^ j / (Nat.factorial j : ℝ) := by
        convert choose_le_pow_div_factorial ( Int.toNat ( u i ) ) j using 1 <;> (try (first | with_reducible_and_instances rfl | (show (_ : LE ℝ) = _; rfl) | (show (_ : LT ℝ) = _; rfl) | (show (_ : LE ℝ) = _; with_unfolding_all rfl) | (show (_ : LT ℝ) = _; with_unfolding_all rfl)))
      generalize_proofs at *; (
      exact h_choose_bound.trans ( by gcongr ; linarith [ hu_range i, show ( u i |> Int.toNat : ℝ ) ≤ M from by linarith [ hu_range i, show ( u i |> Int.toNat : ℝ ) = u i from mod_cast Int.toNat_of_nonneg ( hu_range i |>.1 ) ] ] ));
    exact fun i => pow_le_pow_left₀ ( by positivity ) ( mul_le_mul ( hw_bound i ) ( h_binom_bound i ) ( by positivity ) ( by positivity ) ) _;
  convert Finset.sum_le_sum fun i _ => h_term_bound i using 1 <;> (try (first | with_reducible_and_instances rfl | (show (_ : LE ℝ) = _; rfl) | (show (_ : LT ℝ) = _; rfl) | (show (_ : LE ℝ) = _; with_unfolding_all rfl) | (show (_ : LT ℝ) = _; with_unfolding_all rfl))) ; norm_num ; ring