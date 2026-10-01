import Mathlib

theorem lag_test (n j : ℕ) (hj : j ≤ n) :
    (((-1 : ℚ) ^ j * (2 : ℚ) ^ (j * (j - 1) / 2) *
        ∏ i ∈ Finset.range j, ((2 : ℚ) ^ (n - i) - 1) / ((2 : ℚ) ^ (i + 1) - 1)) *
      ∏ i ∈ Finset.range n, ((2 : ℚ) ^ (2 * n - j - i) - 1) / ((2 : ℚ) ^ (i + 1) - 1)) * 2 ^ j *
      (∏ l ∈ Finset.range j, ((2 : ℚ) ^ j - 2 ^ l)) *
      ∏ s ∈ Finset.range (n - j), ((2 : ℚ) ^ j - 2 ^ (j + 1 + s)) =
    ∏ i ∈ Finset.range n, ((2 : ℚ) ^ j - 2 ^ (n + 1 + i)) := by
  have hpos : ∀ s : ℕ, (2 : ℚ) ^ (s + 1) - 1 ≠ 0 := by
    intro s
    have : (2 : ℚ) ≤ 2 ^ (s + 1) := by
      calc (2 : ℚ) = 2 ^ 1 := by norm_num
        _ ≤ 2 ^ (s + 1) := pow_le_pow_right₀ (by norm_num) (by omega)
    linarith
  -- (b) the nodes below j
  have hb : ∏ l ∈ Finset.range j, ((2 : ℚ) ^ j - 2 ^ l) =
      (2 : ℚ) ^ (j * (j - 1) / 2) * ∏ s ∈ Finset.range j, ((2 : ℚ) ^ (s + 1) - 1) := by
    have h1 : ∀ l ∈ Finset.range j, ((2 : ℚ) ^ j - 2 ^ l) = 2 ^ l * ((2 : ℚ) ^ (j - l) - 1) := by
      intro l hl
      have hl' := Finset.mem_range.mp hl
      have : (2 : ℚ) ^ j = 2 ^ l * 2 ^ (j - l) := by rw [← pow_add]; congr 1; omega
      rw [this]; ring
    rw [Finset.prod_congr rfl h1, Finset.prod_mul_distrib, Finset.prod_pow_eq_pow_sum,
      Finset.sum_range_id]
    congr 1
    rw [← Finset.prod_range_reflect]
    refine Finset.prod_congr rfl (fun s hs => ?_)
    have hs' := Finset.mem_range.mp hs
    congr 2
    omega
  -- (c) the nodes above j
  have hc : ∏ s ∈ Finset.range (n - j), ((2 : ℚ) ^ j - 2 ^ (j + 1 + s)) =
      (-(2 : ℚ) ^ j) ^ (n - j) * ∏ s ∈ Finset.range (n - j), ((2 : ℚ) ^ (s + 1) - 1) := by
    calc ∏ s ∈ Finset.range (n - j), ((2 : ℚ) ^ j - 2 ^ (j + 1 + s))
        = ∏ s ∈ Finset.range (n - j), ((-(2 : ℚ) ^ j) * ((2 : ℚ) ^ (s + 1) - 1)) := by
          refine Finset.prod_congr rfl (fun s _ => ?_)
          rw [show j + 1 + s = j + (s + 1) by omega, pow_add]
          ring
      _ = _ := by rw [Finset.prod_mul_distrib, Finset.prod_const, Finset.card_range]
  -- (d) the right side
  have hd : ∏ i ∈ Finset.range n, ((2 : ℚ) ^ j - 2 ^ (n + 1 + i)) =
      (-(2 : ℚ) ^ j) ^ n * ∏ i ∈ Finset.range n, ((2 : ℚ) ^ (n + 1 + i - j) - 1) := by
    calc ∏ i ∈ Finset.range n, ((2 : ℚ) ^ j - 2 ^ (n + 1 + i))
        = ∏ i ∈ Finset.range n, ((-(2 : ℚ) ^ j) * ((2 : ℚ) ^ (n + 1 + i - j) - 1)) := by
          refine Finset.prod_congr rfl (fun i _ => ?_)
          rw [show n + 1 + i = j + (n + 1 + i - j) by omega, pow_add, Nat.add_sub_cancel_left]
          ring
      _ = _ := by rw [Finset.prod_mul_distrib, Finset.prod_const, Finset.card_range]
  -- (e) the q-factorial splits at j
  have he : (∏ i ∈ Finset.range j, ((2 : ℚ) ^ (n - i) - 1)) *
      ∏ s ∈ Finset.range (n - j), ((2 : ℚ) ^ (s + 1) - 1) =
      ∏ s ∈ Finset.range n, ((2 : ℚ) ^ (s + 1) - 1) := by
    have hn : n = (n - j) + j := by omega
    conv_rhs => rw [hn]
    rw [Finset.prod_range_add, mul_comm]
    congr 1
    rw [← Finset.prod_range_reflect]
    refine Finset.prod_congr rfl (fun t ht => ?_)
    have ht' := Finset.mem_range.mp ht
    congr 2
    omega
  -- (f) reflect the second Gaussian binomial's numerator
  have hf : ∏ i ∈ Finset.range n, ((2 : ℚ) ^ (2 * n - j - i) - 1) =
      ∏ i ∈ Finset.range n, ((2 : ℚ) ^ (n + 1 + i - j) - 1) := by
    rw [← Finset.prod_range_reflect]
    refine Finset.prod_congr rfl (fun i hi => ?_)
    have hi' := Finset.mem_range.mp hi
    congr 2
    omega
  have hF : ∏ s ∈ Finset.range n, ((2 : ℚ) ^ (s + 1) - 1) ≠ 0 :=
    Finset.prod_ne_zero_iff.mpr (fun s _ => hpos s)
  have hB : ∏ s ∈ Finset.range j, ((2 : ℚ) ^ (s + 1) - 1) ≠ 0 :=
    Finset.prod_ne_zero_iff.mpr (fun s _ => hpos s)
  have hjj : j * j = j * (j - 1) / 2 + j * (j - 1) / 2 + j := by
    have h2 := Nat.two_mul_div_two_of_even (Nat.even_mul_pred_self j)
    rcases j with _ | j
    · simp
    · simp only [Nat.add_sub_cancel] at h2 ⊢
      nlinarith
  have hpow : (-(2 : ℚ) ^ j) ^ n = (-1) ^ j * 2 ^ (j * (j - 1) / 2) * 2 ^ (j * (j - 1) / 2) * 2 ^ j *
      (-(2 : ℚ) ^ j) ^ (n - j) := by
    rw [show n = j + (n - j) by omega, pow_add, Nat.add_sub_cancel_left, neg_pow, ← pow_mul, hjj,
      pow_add, pow_add]
    ring
  rw [Finset.prod_div_distrib, Finset.prod_div_distrib, hb, hc, hd, hf, hpow]
  field_simp
  rw [← he]
  ring
