
open Polynomial in
theorem pf2_test (n k : ℕ) (hk : k ∈ Finset.range (n + 1)) (x y w : ℕ → ℚ)
    (hx : ∀ a ∈ Finset.range (n + 1), ∀ b ∈ Finset.range (n + 1), x a = x b → a = b)
    (hxy : ∀ i ∈ Finset.range n, x k - y i ≠ 0)
    (hw : ∀ j ∈ Finset.range (n + 1),
      w j * ∏ l ∈ (Finset.range (n + 1)).erase j, (x j - x l) = ∏ i ∈ Finset.range n, (x j - y i)) :
    ∑ j ∈ (Finset.range (n + 1)).erase k, w j / (x k - x j) =
      w k * (∑ i ∈ Finset.range n, 1 / (x k - y i) -
        ∑ l ∈ (Finset.range (n + 1)).erase k, 1 / (x k - x l)) := by
  have hLE := pf_test n x y w hx hw
  set s := Finset.range (n + 1) with hs
  have hne : ∀ j ∈ s, j ≠ k → x k - x j ≠ 0 := by
    intro j hj hjk h
    exact hjk (hx j hj k hk (sub_eq_zero.mp h).symm)
  set P := ∏ l ∈ s.erase k, (x k - x l) with hP
  have hP0 : P ≠ 0 := Finset.prod_ne_zero_iff.mpr (fun l hl =>
    hne l (Finset.mem_of_mem_erase hl) (Finset.ne_of_mem_erase hl))
  have hd := congrArg (fun p => (derivative p).eval (x k)) hLE
  simp only [derivative_sum, derivative_mul, derivative_C, zero_mul, zero_add, derivative_prod_finset,
    derivative_sub, derivative_X, sub_zero, mul_one, eval_finset_sum, eval_mul, eval_C, eval_prod,
    eval_sub, eval_X] at hd
  -- the terms j ≠ k
  have h1 : ∀ j ∈ s.erase k, (∑ m ∈ s.erase j, ∏ l ∈ (s.erase j).erase m, (x k - x l)) =
      P * (1 / (x k - x j)) := by
    intro j hj
    have hjs := Finset.mem_of_mem_erase hj
    have hjk := Finset.ne_of_mem_erase hj
    have hks : k ∈ s.erase j := Finset.mem_erase.mpr ⟨Ne.symm hjk, hk⟩
    rw [Finset.sum_eq_single k]
    · have := Finset.mul_prod_erase (s.erase k) (fun l => x k - x l) hj
      rw [Finset.erase_right_comm]
      field_simp [hne j hjs hjk]
      rw [hP, ← this]
      ring
    · intro m hm hmk
      exact Finset.prod_eq_zero (i := k) (Finset.mem_erase.mpr ⟨Ne.symm hmk, hks⟩) (sub_self _)
    · intro h; exact absurd hks h
  -- the term j = k
  have h2 : (∑ m ∈ s.erase k, ∏ l ∈ (s.erase k).erase m, (x k - x l)) =
      P * ∑ m ∈ s.erase k, 1 / (x k - x m) := by
    rw [Finset.mul_sum]
    refine Finset.sum_congr rfl (fun m hm => ?_)
    have := Finset.mul_prod_erase (s.erase k) (fun l => x k - x l) hm
    field_simp [hne m (Finset.mem_of_mem_erase hm) (Finset.ne_of_mem_erase hm)]
    rw [hP, ← this]
    ring
  -- the right side
  have h3 : (∑ i ∈ Finset.range n, ∏ i' ∈ (Finset.range n).erase i, (x k - y i')) =
      (w k * P) * ∑ i ∈ Finset.range n, 1 / (x k - y i) := by
    rw [hw k hk, Finset.mul_sum]
    refine Finset.sum_congr rfl (fun i hi => ?_)
    have := Finset.mul_prod_erase (Finset.range n) (fun i' => x k - y i') hi
    field_simp [hxy i hi]
    rw [← this]
    ring
  rw [← Finset.add_sum_erase s _ hk, h2, h3] at hd
  have h1' : ∑ j ∈ s.erase k, w j * ∑ m ∈ s.erase j, ∏ l ∈ (s.erase j).erase m, (x k - x l) =
      P * ∑ j ∈ s.erase k, w j / (x k - x j) := by
    rw [Finset.mul_sum]
    refine Finset.sum_congr rfl (fun j hj => ?_)
    rw [h1 j hj]
    ring
  rw [h1'] at hd
  apply mul_left_cancel₀ hP0
  linear_combination hd
