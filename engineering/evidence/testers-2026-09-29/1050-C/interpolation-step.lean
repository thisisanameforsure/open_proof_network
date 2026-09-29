import Mathlib

open Polynomial in
theorem pf_test (n : ℕ) (x y w : ℕ → ℚ) (hx : ∀ a ∈ Finset.range (n + 1), ∀ b ∈ Finset.range (n + 1), x a = x b → a = b)
    (hw : ∀ j ∈ Finset.range (n + 1),
      w j * ∏ l ∈ (Finset.range (n + 1)).erase j, (x j - x l) = ∏ i ∈ Finset.range n, (x j - y i)) :
    (∑ j ∈ Finset.range (n + 1), C (w j) * ∏ l ∈ (Finset.range (n + 1)).erase j, (X - C (x l))) =
      ∏ i ∈ Finset.range n, (X - C (y i)) := by
  set s := Finset.range (n + 1) with hs
  have hL : (∑ j ∈ s, C (w j) * ∏ l ∈ s.erase j, (X - C (x l))).natDegree ≤ n := by
    refine natDegree_sum_le_of_forall_le _ _ (fun j hj => ?_)
    refine (natDegree_C_mul_le _ _).trans ((natDegree_prod_le _ _).trans ?_)
    simp only [natDegree_X_sub_C, Finset.sum_const, smul_eq_mul, mul_one]
    rw [Finset.card_erase_of_mem hj, hs, Finset.card_range]
    omega
  have hE : (∏ i ∈ Finset.range n, (X - C (y i))).natDegree ≤ n := by
    refine (natDegree_prod_le _ _).trans ?_
    simp [natDegree_X_sub_C]
  apply Polynomial.eq_of_degree_sub_lt_of_eval_finset_eq (s.image x)
  · rw [Finset.card_image_of_injOn (fun a ha b hb h => hx a ha b hb h), hs, Finset.card_range]
    refine lt_of_le_of_lt (degree_sub_le _ _) (max_lt ?_ ?_)
    · exact lt_of_le_of_lt (degree_le_of_natDegree_le hL) (by exact_mod_cast Nat.lt_succ_self n)
    · exact lt_of_le_of_lt (degree_le_of_natDegree_le hE) (by exact_mod_cast Nat.lt_succ_self n)
  · intro z hz
    obtain ⟨j, hj, rfl⟩ := Finset.mem_image.mp hz
    simp only [eval_finset_sum, eval_mul, eval_C, eval_prod, eval_sub, eval_X]
    rw [Finset.sum_eq_single j]
    · exact hw j hj
    · intro i hi hij
      rw [Finset.prod_eq_zero (i := j) (Finset.mem_erase.mpr ⟨Ne.symm hij, hj⟩) (sub_self _), mul_zero]
    · intro hj'; exact absurd hj hj'
