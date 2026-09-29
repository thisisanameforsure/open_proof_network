import Mathlib

theorem hA_test (n k i : ℕ) (hk : k ≤ n) (hi : i < n)
    (gauss : ∀ N r : ℕ, ∃ z : ℤ,
      (z : ℚ) = ∏ t ∈ Finset.range r, ((2 : ℚ) ^ (N - t) - 1) / ((2 : ℚ) ^ (t + 1) - 1))
    (M : ℕ → ℕ) (hM : M = fun n => ∏ m ∈ Finset.Ioc (n / 2) n, (2 ^ m - 1)) :
    ∃ w : ℤ, (w : ℚ) * ((2 : ℚ) ^ (n + 1 + i - k) - 1) = (M n : ℚ) *
      ∏ j ∈ Finset.range n, ((2 : ℚ) ^ (2 * n - k - j) - 1) / ((2 : ℚ) ^ (j + 1) - 1) := by
  set h := n / 2 with hh
  set m := 2 * n - k with hm
  have hden : ∀ s : ℕ, (2 : ℚ) ^ (s + 1) - 1 ≠ 0 := by
    intro s
    have : (2 : ℚ) ≤ 2 ^ (s + 1) := by
      calc (2 : ℚ) = 2 ^ 1 := by norm_num
        _ ≤ 2 ^ (s + 1) := pow_le_pow_right₀ (by norm_num) (by omega)
    linarith
  -- M n in ℚ
  have hMq : (M n : ℚ) = ∏ j ∈ Finset.Ioc h n, ((2 : ℚ) ^ j - 1) := by
    rw [hM]
    push_cast
    refine Finset.prod_congr rfl (fun j _ => ?_)
    rw [Nat.cast_sub Nat.one_le_two_pow]
    push_cast
    ring
  -- (2;2)_n = (2;2)_h · M n
  have hsplit : ∏ s ∈ Finset.range n, ((2 : ℚ) ^ (s + 1) - 1) =
      (∏ s ∈ Finset.range h, ((2 : ℚ) ^ (s + 1) - 1)) * ∏ j ∈ Finset.Ioc h n, ((2 : ℚ) ^ j - 1) := by
    have hI : Finset.Ioc h n = Finset.Ico (h + 1) (n + 1) := by
      ext j; simp only [Finset.mem_Ioc, Finset.mem_Ico]; omega
    rw [hI, Finset.prod_Ico_eq_prod_range, show n + 1 - (h + 1) = n - h by omega]
    conv_lhs => rw [show n = h + (n - h) by omega]
    rw [Finset.prod_range_add]
    congr 1
    refine Finset.prod_congr rfl (fun t _ => ?_)
    rw [show h + t + 1 = h + 1 + t by omega]
  set i1 := n - 1 - i with hi1
  have ha : m - i1 = n + 1 + i - k := by omega
  have hnum : ∏ j ∈ Finset.range n, ((2 : ℚ) ^ (m - j) - 1) =
      (∏ j ∈ Finset.range i1, ((2 : ℚ) ^ (m - j) - 1)) * ((2 : ℚ) ^ (m - i1) - 1) *
        ∏ t ∈ Finset.range (n - 1 - i1), ((2 : ℚ) ^ (m - (i1 + 1 + t)) - 1) := by
    conv_lhs => rw [show n = (i1 + 1) + (n - 1 - i1) by omega]
    rw [Finset.prod_range_add, Finset.prod_range_succ]
  have hQh : ∏ s ∈ Finset.range h, ((2 : ℚ) ^ (s + 1) - 1) ≠ 0 :=
    Finset.prod_ne_zero_iff.mpr (fun s _ => hden s)
  have hPM : ∏ j ∈ Finset.Ioc h n, ((2 : ℚ) ^ j - 1) ≠ 0 := by
    refine Finset.prod_ne_zero_iff.mpr (fun j hj => ?_)
    have hj1 := (Finset.mem_Ioc.mp hj).1
    rw [show j = (j - 1) + 1 by omega]
    exact hden _
  rw [Finset.prod_div_distrib, hsplit, hMq, hnum, ha]
  rcases Nat.lt_or_ge i1 h with hlt | hge
  · -- the run above i1 holds h consecutive exponents
    obtain ⟨z0, hz0⟩ := gauss (m - i1 - 1) h
    rw [Finset.prod_div_distrib] at hz0
    have hY : ∏ t ∈ Finset.range (n - 1 - i1), ((2 : ℚ) ^ (m - (i1 + 1 + t)) - 1) =
        (∏ t ∈ Finset.range h, ((2 : ℚ) ^ (m - i1 - 1 - t) - 1)) *
          ∏ t ∈ Finset.range (n - 1 - i1 - h), ((2 : ℚ) ^ (m - (i1 + 1 + (h + t))) - 1) := by
      conv_lhs => rw [show n - 1 - i1 = h + (n - 1 - i1 - h) by omega]
      rw [Finset.prod_range_add]
      congr 1
      refine Finset.prod_congr rfl (fun t _ => ?_)
      rw [show m - (i1 + 1 + t) = m - i1 - 1 - t by omega]
    refine ⟨z0 * (∏ j ∈ Finset.range i1, ((2 : ℤ) ^ (m - j) - 1)) *
      ∏ t ∈ Finset.range (n - 1 - i1 - h), ((2 : ℤ) ^ (m - (i1 + 1 + (h + t))) - 1), ?_⟩
    push_cast
    rw [hz0, hY]
    field_simp
  · -- the run below i1 holds h consecutive exponents
    obtain ⟨z0, hz0⟩ := gauss m h
    rw [Finset.prod_div_distrib] at hz0
    have hX : ∏ j ∈ Finset.range i1, ((2 : ℚ) ^ (m - j) - 1) =
        (∏ j ∈ Finset.range h, ((2 : ℚ) ^ (m - j) - 1)) *
          ∏ t ∈ Finset.range (i1 - h), ((2 : ℚ) ^ (m - (h + t)) - 1) := by
      conv_lhs => rw [show i1 = h + (i1 - h) by omega]
      rw [Finset.prod_range_add]
    refine ⟨z0 * (∏ t ∈ Finset.range (i1 - h), ((2 : ℤ) ^ (m - (h + t)) - 1)) *
      ∏ t ∈ Finset.range (n - 1 - i1), ((2 : ℤ) ^ (m - (i1 + 1 + t)) - 1), ?_⟩
    push_cast
    rw [hz0, hX]
    field_simp
