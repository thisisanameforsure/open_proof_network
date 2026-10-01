import Mathlib
open Polynomial

theorem lagrange_fp (s : Finset ℕ) (x : ℕ → ℚ) (hx : Set.InjOn x s) (r : ℕ → ℚ) (N : ℚ[X])
    (hN : N.natDegree < s.card)
    (hr : ∀ j ∈ s, r j * ∏ i ∈ s.erase j, (x j - x i) = N.eval (x j)) :
    N = ∑ j ∈ s, C (r j) * ∏ i ∈ s.erase j, (X - C (x i)) := by
  have hdeg : (∑ j ∈ s, C (r j) * ∏ i ∈ s.erase j, (X - C (x i)) - N).natDegree < s.card := by
    have hs : 0 < s.card := by
      rcases Nat.eq_zero_or_pos s.card with h | h
      · omega
      · exact h
    refine lt_of_le_of_lt (natDegree_sub_le _ _) (max_lt ?_ hN)
    refine lt_of_le_of_lt (natDegree_sum_le_of_forall_le s _ (n := s.card - 1) ?_) (by omega)
    intro j hj
    refine (natDegree_C_mul_le _ _).trans ?_
    rw [natDegree_finsetProd_X_sub_C_eq_card, Finset.card_erase_of_mem hj]
  have hzero : ∑ j ∈ s, C (r j) * ∏ i ∈ s.erase j, (X - C (x i)) - N = 0 := by
    apply eq_zero_of_natDegree_lt_card_of_eval_eq_zero' _ (s.image x)
    · intro y hy
      obtain ⟨i, hi, rfl⟩ := Finset.mem_image.1 hy
      rw [eval_sub, eval_finsetSum, Finset.sum_eq_single i]
      · rw [eval_mul, eval_C, eval_prod]
        simp only [eval_sub, eval_X, eval_C]
        rw [hr i hi, sub_self]
      · intro j hj hji
        rw [eval_mul, eval_prod]
        apply mul_eq_zero_of_right
        apply Finset.prod_eq_zero (i := i)
        · exact Finset.mem_erase.2 ⟨Ne.symm hji, hi⟩
        · simp
      · intro h; exact absurd hi h
    · rw [Finset.card_image_of_injOn hx]; exact hdeg
  exact (sub_eq_zero.1 hzero).symm

theorem deriv_eval (s : Finset ℕ) (x : ℕ → ℚ) (hx : Set.InjOn x s) (r : ℕ → ℚ) (k : ℕ) (hk : k ∈ s) :
    (derivative (∑ j ∈ s, C (r j) * ∏ i ∈ s.erase j, (X - C (x i)))).eval (x k) =
      (∏ i ∈ s.erase k, (x k - x i)) *
        (∑ j ∈ s.erase k, r j / (x k - x j) + r k * ∑ i ∈ s.erase k, 1 / (x k - x i)) := by
  have hne : ∀ i ∈ s.erase k, x k - x i ≠ 0 := by
    intro i hi h
    have hik := (Finset.mem_erase.1 hi)
    exact hik.1 (hx hik.2 hk (sub_eq_zero.1 h).symm)
  have hD : ∀ a ∈ s.erase k, ∏ b ∈ (s.erase k).erase a, (x k - x b) = (∏ i ∈ s.erase k, (x k - x i)) / (x k - x a) := by
    intro a ha
    rw [eq_div_iff (hne a ha), mul_comm]
    exact Finset.mul_prod_erase (s.erase k) (fun b => x k - x b) ha
  rw [derivative_sum, eval_finsetSum, ← Finset.add_sum_erase _ _ hk]
  have hterm : ∀ j ∈ s.erase k, (derivative (C (r j) * ∏ i ∈ s.erase j, (X - C (x i)))).eval (x k) =
      r j * ((∏ i ∈ s.erase k, (x k - x i)) / (x k - x j)) := by
    intro j hj
    rw [derivative_C_mul, eval_mul, eval_C, derivative_prod_finset, eval_finsetSum]
    congr 1
    have hkj : k ∈ s.erase j := Finset.mem_erase.2 ⟨fun h => (Finset.mem_erase.1 hj).1 h.symm, hk⟩
    rw [Finset.sum_eq_single k]
    · rw [derivative_X_sub_C, mul_one, eval_prod]
      simp only [eval_sub, eval_X, eval_C]
      rw [Finset.erase_right_comm]
      exact hD j hj
    · intro a ha hak
      rw [eval_mul, eval_prod]
      apply mul_eq_zero_of_left
      apply Finset.prod_eq_zero (i := k)
      · exact Finset.mem_erase.2 ⟨fun h => hak h.symm, hkj⟩
      · simp
    · intro h; exact absurd hkj h
  rw [Finset.sum_congr rfl hterm]
  rw [derivative_C_mul, eval_mul, eval_C, derivative_prod_finset, eval_finsetSum]
  have hself : ∀ a ∈ s.erase k, ((∏ b ∈ (s.erase k).erase a, (X - C (x b))) * derivative (X - C (x a))).eval (x k) =
      (∏ i ∈ s.erase k, (x k - x i)) / (x k - x a) := by
    intro a ha
    rw [derivative_X_sub_C, mul_one, eval_prod]
    simp only [eval_sub, eval_X, eval_C]
    exact hD a ha
  rw [Finset.sum_congr rfl hself]
  rw [mul_add, add_comm]
  congr 1
  · rw [Finset.mul_sum]
    apply Finset.sum_congr rfl
    intro j _
    ring
  · rw [Finset.mul_sum, Finset.mul_sum, Finset.mul_sum]
    apply Finset.sum_congr rfl
    intro j _
    ring
