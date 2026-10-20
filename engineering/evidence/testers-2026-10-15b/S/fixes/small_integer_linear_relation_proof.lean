theorem small_integer_linear_relation_proof
    (r : ℕ) (hr : 1 ≤ r)
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
  by_cases hr2 : r ≥ 2;
  · convert silr_lattice_case r hr2 s hs M hM W hW u w hu_range hu_strict hw_pos hw_bound using 1 <;> (try (first | with_reducible_and_instances rfl | (show (_ : LE ℝ) = _; rfl) | (show (_ : LT ℝ) = _; rfl) | (show (_ : LE ℝ) = _; with_unfolding_all rfl) | (show (_ : LT ℝ) = _; with_unfolding_all rfl)));
  · interval_cases r ; subst hs;
    refine' ⟨ fun i => if i = 0 then w 1 else -w 0, _, _, _ ⟩ <;> simp_all +decide [ Fin.sum_univ_succ ];
    · ring;
    · nlinarith [ show ( w 0 : ℝ ) * w 1 > 0 by exact mul_pos ( Nat.cast_pos.mpr hw_pos.1 ) ( Nat.cast_pos.mpr hw_pos.2 ), show ( u 0 : ℝ ) < u 1 by exact_mod_cast hu_strict ( by decide ) ]
