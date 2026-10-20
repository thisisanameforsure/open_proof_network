lemma silr_lattice_case
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
      (∀ i, |(a i : ℝ)| ≤ (256 * M / (r : ℝ)) ^ (r - 1 : ℕ) * W) := by
  obtain ⟨a, ha⟩ := lattice_core r hr s hs M hM W hW u w hu_range hu_strict hw_pos hw_bound;
  refine' ⟨ a, ha.1, ha.2.1, _ ⟩;
  intro i
  have h_sq : (a i : ℝ) ^ 2 ≤ (∑ j : Fin s, (a j : ℝ) ^ 2) := by
    exact_mod_cast Finset.single_le_sum ( fun i _ => sq_nonneg ( a i ) ) ( Finset.mem_univ i );
  have h_abs : (a i : ℝ) ^ (2 * r) ≤ ((256 * M / r) ^ (r - 1) * W) ^ (2 * r) := by
    convert le_trans _ ( ha.2.2.trans _ ) using 1 <;> (try (first | with_reducible_and_instances rfl | (show (_ : LE ℝ) = _; rfl) | (show (_ : LT ℝ) = _; rfl) | (show (_ : LE ℝ) = _; with_unfolding_all rfl) | (show (_ : LT ℝ) = _; with_unfolding_all rfl)));
    · simpa only [ pow_mul ] using pow_le_pow_left₀ ( sq_nonneg _ ) h_sq _;
    · convert lattice_bound_implies_coord_bound r hr M W ( by linarith [ show ( s : ℝ ) ≥ 2 * 2 by norm_cast; linarith ] ) ( by linarith ) using 1 <;> (try (first | with_reducible_and_instances rfl | (show (_ : LE ℝ) = _; rfl) | (show (_ : LT ℝ) = _; rfl) | (show (_ : LE ℝ) = _; with_unfolding_all rfl) | (show (_ : LT ℝ) = _; with_unfolding_all rfl)));
  contrapose! h_abs;
  convert pow_lt_pow_left₀ h_abs ( mul_nonneg ( pow_nonneg ( div_nonneg ( mul_nonneg ( by norm_num ) ( show 0 ≤ M by linarith [ show ( s : ℝ ) ≥ 2 by norm_cast; linarith ] ) ) ( Nat.cast_nonneg _ ) ) _ ) ( by positivity ) ) ( by positivity : ( 2 * r ) ≠ 0 ) using 1 <;> (try (first | with_reducible_and_instances rfl | (show (_ : LE ℝ) = _; rfl) | (show (_ : LT ℝ) = _; rfl) | (show (_ : LE ℝ) = _; with_unfolding_all rfl) | (show (_ : LT ℝ) = _; with_unfolding_all rfl))) ; norm_num [ pow_mul ]