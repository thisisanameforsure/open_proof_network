import Mathlib

theorem id1_test (n j : ℕ) (hj : j ≤ n) :
    (∏ i ∈ Finset.range j, ((2 : ℚ) ^ (n - i) - 1)) * ∏ s ∈ Finset.range (n - j), ((2 : ℚ) ^ (s + 1) - 1) =
      ∏ s ∈ Finset.range n, ((2 : ℚ) ^ (s + 1) - 1) := by
  induction j with
  | zero => simp
  | succ j ih =>
    have ih' := ih (by omega)
    rw [Finset.prod_range_succ, ← ih']
    obtain ⟨m, hm⟩ : ∃ m, n - j = m + 1 := ⟨n - j - 1, by omega⟩
    rw [hm, Finset.prod_range_succ, show n - (j + 1) = m by omega]
    ring

theorem lower_test (j : ℕ) :
    ∏ i ∈ Finset.range j, ((2 : ℚ) ^ j - 2 ^ i) =
      2 ^ (j * (j - 1) / 2) * ∏ s ∈ Finset.range j, ((2 : ℚ) ^ (s + 1) - 1) := by
  have h1 : ∀ i ∈ Finset.range j, ((2 : ℚ) ^ j - 2 ^ i) = 2 ^ i * (2 ^ (j - 1 - i + 1) - 1) := by
    intro i hi
    have hi' := Finset.mem_range.mp hi
    rw [mul_sub, ← pow_add, show i + (j - 1 - i + 1) = j by omega]
    ring
  rw [Finset.prod_congr rfl h1, Finset.prod_mul_distrib, Finset.prod_pow_eq_pow_sum,
    Finset.prod_range_reflect (fun s => ((2 : ℚ) ^ (s + 1) - 1)) j]
  congr 1
  congr 1
  have := Finset.sum_range_id_mul_two j
  omega

theorem upper_test (j n : ℕ) (hj : j ≤ n) :
    ∏ i ∈ Finset.Ioc j n, ((2 : ℚ) ^ j - 2 ^ i) =
      (-1) ^ (n - j) * 2 ^ (j * (n - j)) * ∏ s ∈ Finset.range (n - j), ((2 : ℚ) ^ (s + 1) - 1) := by
  have e : Finset.Ioc j n = Finset.Ico (j + 1) (n + 1) := by
    ext x; simp only [Finset.mem_Ioc, Finset.mem_Ico]; omega
  rw [e, Finset.prod_Ico_eq_prod_range, show n + 1 - (j + 1) = n - j by omega]
  have h1 : ∀ t ∈ Finset.range (n - j), ((2 : ℚ) ^ j - 2 ^ (j + 1 + t)) = (-1) * 2 ^ j * (2 ^ (t + 1) - 1) := by
    intro t _
    rw [show j + 1 + t = j + (t + 1) by ring, pow_add]
    ring
  rw [Finset.prod_congr rfl h1, Finset.prod_mul_distrib, Finset.prod_mul_distrib, Finset.prod_const,
    Finset.prod_const, Finset.card_range, ← pow_mul]

theorem rhs_test (j n : ℕ) (hj : j ≤ n) :
    (∏ K ∈ Finset.Ioc n (2 * n), ((2 : ℚ) ^ j - 2 ^ K)) *
      ∏ s ∈ Finset.range (n - j), ((2 : ℚ) ^ (s + 1) - 1) =
      (-1) ^ n * 2 ^ (j * n) * ∏ s ∈ Finset.range (2 * n - j), ((2 : ℚ) ^ (s + 1) - 1) := by
  have e : Finset.Ioc n (2 * n) = Finset.Ico (n + 1) (2 * n + 1) := by
    ext x; simp only [Finset.mem_Ioc, Finset.mem_Ico]; omega
  rw [e, Finset.prod_Ico_eq_prod_range, show 2 * n + 1 - (n + 1) = n by omega]
  have h1 : ∀ t ∈ Finset.range n, ((2 : ℚ) ^ j - 2 ^ (n + 1 + t)) =
      (-1) * 2 ^ j * (2 ^ ((n - j) + t + 1) - 1) := by
    intro t _
    rw [show n + 1 + t = j + ((n - j) + t + 1) by omega, pow_add]
    ring
  rw [Finset.prod_congr rfl h1, Finset.prod_mul_distrib, Finset.prod_mul_distrib, Finset.prod_const,
    Finset.prod_const, Finset.card_range, ← pow_mul,
    show 2 * n - j = (n - j) + n by omega, Finset.prod_range_add]
  ring

theorem id1_full (n j : ℕ) (hj : j ≤ n) :
    (((-1 : ℚ) ^ j * (2 : ℚ) ^ (j * (j - (1 : ℕ)) / (2 : ℕ)) *
          ∏ i ∈ Finset.range j, ((2 : ℚ) ^ (n - i) - (1 : ℚ)) / ((2 : ℚ) ^ (i + (1 : ℕ)) - (1 : ℚ))) *
        ∏ i ∈ Finset.range n, ((2 : ℚ) ^ ((2 : ℕ) * n - j - i) - (1 : ℚ)) / ((2 : ℚ) ^ (i + (1 : ℕ)) - (1 : ℚ))) *
      2 ^ j * ∏ i ∈ (Finset.range (n + 1)).erase j, ((2 : ℚ) ^ j - 2 ^ i) =
    ∏ K ∈ Finset.Ioc n (2 * n), ((2 : ℚ) ^ j - 2 ^ K) := by
  have hPne : ∀ m : ℕ, ∏ s ∈ Finset.range m, ((2 : ℚ) ^ (s + 1) - 1) ≠ 0 := by
    intro m
    refine Finset.prod_ne_zero_iff.mpr (fun s _ => ?_)
    have : (1 : ℚ) < 2 ^ (s + 1) := one_lt_pow₀ (by norm_num) (by omega)
    linarith
  have hG1 : ∏ i ∈ Finset.range j, ((2 : ℚ) ^ (n - i) - (1 : ℚ)) / ((2 : ℚ) ^ (i + (1 : ℕ)) - (1 : ℚ)) =
      (∏ s ∈ Finset.range n, ((2 : ℚ) ^ (s + 1) - 1)) /
        ((∏ s ∈ Finset.range (n - j), ((2 : ℚ) ^ (s + 1) - 1)) * ∏ s ∈ Finset.range j, ((2 : ℚ) ^ (s + 1) - 1)) := by
    rw [Finset.prod_div_distrib, ← id1_test n j hj]
    field_simp [hPne]
  have hG2 : ∏ i ∈ Finset.range n, ((2 : ℚ) ^ ((2 : ℕ) * n - j - i) - (1 : ℚ)) / ((2 : ℚ) ^ (i + (1 : ℕ)) - (1 : ℚ)) =
      (∏ s ∈ Finset.range (2 * n - j), ((2 : ℚ) ^ (s + 1) - 1)) /
        ((∏ s ∈ Finset.range (n - j), ((2 : ℚ) ^ (s + 1) - 1)) * ∏ s ∈ Finset.range n, ((2 : ℚ) ^ (s + 1) - 1)) := by
    rw [Finset.prod_div_distrib, ← id1_test (2 * n - j) n (by omega), show 2 * n - j - n = n - j by omega]
    field_simp [hPne]
  have hsplit : (Finset.range (n + 1)).erase j = Finset.range j ∪ Finset.Ioc j n := by
    ext x; simp only [Finset.mem_erase, Finset.mem_range, Finset.mem_union, Finset.mem_Ioc]; omega
  have hdisj : Disjoint (Finset.range j) (Finset.Ioc j n) := by
    rw [Finset.disjoint_left]
    intro x hx hx'
    simp only [Finset.mem_range, Finset.mem_Ioc] at hx hx'
    omega
  have hR := rhs_test j n hj
  obtain ⟨m, rfl⟩ := Nat.exists_eq_add_of_le hj
  have hsign : (-1 : ℚ) ^ (j + m) = (-1) ^ j * (-1) ^ (j + m - j) := by
    rw [← pow_add]; congr 1; omega
  have ha : 2 * (j * (j - 1) / 2) = j * (j - 1) := Nat.two_mul_div_two_of_even (Nat.even_mul_pred_self _)
  have hexp : j * (j + m) = j * (j - (1 : ℕ)) / (2 : ℕ) + j + j * (j - (1 : ℕ)) / (2 : ℕ) + j * (j + m - j) := by
    rw [show j + m - j = m by omega]
    rcases j with _ | i
    · simp
    · simp only [Nat.add_sub_cancel] at ha ⊢
      nlinarith [ha]
  rw [hG1, hG2, hsplit, Finset.prod_union hdisj, lower_test, upper_test j (j + m) hj]
  apply mul_right_cancel₀ (hPne (j + m - j))
  rw [hR, hsign, hexp, pow_add, pow_add, pow_add]
  field_simp [hPne]
