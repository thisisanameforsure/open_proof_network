import Mathlib

theorem qx_int (Qc : ℕ → ℕ → ℚ)
    (hQc : Qc = fun (n k : ℕ) =>
      ((-1 : ℚ) ^ k * (2 : ℚ) ^ (k * (k - (1 : ℕ)) / (2 : ℕ)) *
          ∏ i ∈ Finset.range k, ((2 : ℚ) ^ (n - i) - (1 : ℚ)) / ((2 : ℚ) ^ (i + (1 : ℕ)) - (1 : ℚ))) *
        ∏ i ∈ Finset.range n, ((2 : ℚ) ^ ((2 : ℕ) * n - k - i) - (1 : ℚ)) / ((2 : ℚ) ^ (i + (1 : ℕ)) - (1 : ℚ)))
    (n : ℕ) :
    ∃ z : ℤ, (z : ℚ) = (2 : ℚ) ^ (n * (n + 1) / 2) *
      ∑ k ∈ Finset.range (n + (1 : ℕ)), Qc n k * ((3 : ℚ) / (2 : ℚ) ^ n) ^ k := by
  have gauss : ∀ n k : ℕ,
      ∃ z : ℤ, (z : ℚ) = ∏ i ∈ Finset.range k, ((2 : ℚ) ^ (n - i) - 1) / ((2 : ℚ) ^ (i + 1) - 1) := by
    intro n k
    have hD : ∀ j : ℕ, ((2 : ℚ) ^ (j + 1) - 1) ≠ 0 := by
      intro j
      have h1 : (1 : ℚ) < 2 ^ (j + 1) := one_lt_pow₀ (by norm_num) (by omega)
      exact ne_of_gt (sub_pos.mpr h1)
    have hDk : ∀ k : ℕ, (∏ i ∈ Finset.range k, ((2 : ℚ) ^ (i + 1) - 1)) ≠ 0 := by
      intro k
      exact Finset.prod_ne_zero_iff.mpr (fun i _ => hD i)
    have key : ∀ m j : ℕ,
        (∏ i ∈ Finset.range (j + 1), ((2 : ℚ) ^ (m + 1 - i) - 1) / ((2 : ℚ) ^ (i + 1) - 1)) =
          (∏ i ∈ Finset.range j, ((2 : ℚ) ^ (m - i) - 1) / ((2 : ℚ) ^ (i + 1) - 1)) +
          2 ^ (j + 1) *
            ∏ i ∈ Finset.range (j + 1), ((2 : ℚ) ^ (m - i) - 1) / ((2 : ℚ) ^ (i + 1) - 1) := by
      intro m j
      simp only [Finset.prod_div_distrib]
      rw [Finset.prod_range_succ' (fun i => (2 : ℚ) ^ (m + 1 - i) - 1)]
      have hshift : ∀ i : ℕ, m + 1 - (i + 1) = m - i := fun i => by omega
      simp only [hshift, Nat.sub_zero]
      rw [Finset.prod_range_succ (fun i => (2 : ℚ) ^ (m - i) - 1),
        Finset.prod_range_succ (fun i => (2 : ℚ) ^ (i + 1) - 1)]
      have hDj := hDk j
      have hj := hD j
      by_cases hjm : j ≤ m
      · have e : (2 : ℚ) ^ (m + 1) = 2 ^ (m - j) * 2 ^ (j + 1) := by
          rw [← pow_add]
          congr 1
          omega
        rw [e]
        field_simp
        ring
      · have hz : (∏ i ∈ Finset.range j, ((2 : ℚ) ^ (m - i) - 1)) = 0 :=
          Finset.prod_eq_zero (i := m) (Finset.mem_range.mpr (by omega)) (by simp)
        rw [hz]
        simp
    have main : ∀ m j : ℕ, ∃ z : ℤ,
        (z : ℚ) = ∏ i ∈ Finset.range j, ((2 : ℚ) ^ (m - i) - 1) / ((2 : ℚ) ^ (i + 1) - 1) := by
      intro m
      induction m with
      | zero =>
        intro j
        cases j with
        | zero => exact ⟨1, by simp⟩
        | succ j =>
          refine ⟨0, ?_⟩
          rw [Finset.prod_eq_zero (i := 0) (by simp) (by simp)]
          simp
      | succ m ih =>
        intro j
        cases j with
        | zero => exact ⟨1, by simp⟩
        | succ j =>
          obtain ⟨a, ha⟩ := ih j
          obtain ⟨b, hb⟩ := ih (j + 1)
          refine ⟨a + 2 ^ (j + 1) * b, ?_⟩
          rw [key, ← ha, ← hb]
          push_cast
          ring
    exact main n k
  have hterm : ∀ k ∈ Finset.range (n + 1), ∃ z : ℤ,
      (z : ℚ) = (2 : ℚ) ^ (n * (n + 1) / 2) * (Qc n k * ((3 : ℚ) / (2 : ℚ) ^ n) ^ k) := by
    intro k hk
    have hkn : k ≤ n := Nat.lt_succ_iff.mp (Finset.mem_range.mp hk)
    obtain ⟨a, ha⟩ := gauss n k
    obtain ⟨b, hb⟩ := gauss (2 * n - k) n
    obtain ⟨m, rfl⟩ := Nat.exists_eq_add_of_le hkn
    have hexp : (k + m) * (k + m + 1) / 2 + k * (k - 1) / 2 = m * (m + 1) / 2 + (k + m) * k := by
      have e1 : 2 * ((k + m) * (k + m + 1) / 2) = (k + m) * (k + m + 1) :=
        Nat.two_mul_div_two_of_even (Nat.even_mul_succ_self _)
      have e2 : 2 * (k * (k - 1) / 2) = k * (k - 1) :=
        Nat.two_mul_div_two_of_even (Nat.even_mul_pred_self _)
      have e3 : 2 * (m * (m + 1) / 2) = m * (m + 1) :=
        Nat.two_mul_div_two_of_even (Nat.even_mul_succ_self _)
      rcases k with _ | j
      · simp
      · simp only [Nat.add_sub_cancel] at e2 ⊢
        nlinarith [e1, e2, e3]
    refine ⟨(-1) ^ k * 3 ^ k * 2 ^ (m * (m + 1) / 2) * a * b, ?_⟩
    have hpow : (2 : ℚ) ^ ((k + m) * (k + m + 1) / 2) * (2 : ℚ) ^ (k * (k - 1) / 2) =
        (2 : ℚ) ^ (m * (m + 1) / 2) * ((2 : ℚ) ^ (k + m)) ^ k := by
      rw [← pow_add, ← pow_mul, ← pow_add, hexp]
    have h2 : ((2 : ℚ) ^ (k + m)) ≠ 0 := by positivity
    rw [hQc]
    simp only []
    rw [← ha, ← hb]
    push_cast
    rw [div_pow, mul_div_assoc']
    field_simp
    linear_combination -(a : ℚ) * b * hpow
  choose! g hg using hterm
  refine ⟨∑ k ∈ Finset.range (n + 1), g k, ?_⟩
  push_cast
  rw [Finset.mul_sum]
  exact Finset.sum_congr rfl (fun k hk => hg k hk)
