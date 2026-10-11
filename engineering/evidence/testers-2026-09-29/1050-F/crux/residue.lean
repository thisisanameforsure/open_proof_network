import Mathlib

theorem residue (n j : ℕ) (hj : j ≤ n) :
    ((-1 : ℚ) ^ j * (2 : ℚ) ^ (j * (j - 1) / 2) *
        ∏ i ∈ Finset.range j, ((2 : ℚ) ^ (n - i) - 1) / ((2 : ℚ) ^ (i + 1) - 1)) *
      (∏ i ∈ Finset.range n, ((2 : ℚ) ^ (2 * n - j - i) - 1) / ((2 : ℚ) ^ (i + 1) - 1)) * 2 ^ j *
      ∏ i ∈ (Finset.range (n + 1)).erase j, ((2 : ℚ) ^ j - 2 ^ i) =
    ∏ m ∈ Finset.Ico (n + 1) (2 * n + 1), ((2 : ℚ) ^ j - 2 ^ m) := by
  obtain ⟨r, rfl⟩ : ∃ r, n = r + j := ⟨n - j, by omega⟩
  -- q-factorial P b = ∏_{i<b} (2^(i+1) - 1), and the shifted block U r b = ∏_{s<b} (2^(r+1+s) - 1)
  have hPne : ∀ b : ℕ, (∏ i ∈ Finset.range b, ((2 : ℚ) ^ (i + 1) - 1)) ≠ 0 := by
    intro b
    rw [Finset.prod_ne_zero_iff]
    intro i _
    have : (1 : ℚ) < 2 ^ (i + 1) := one_lt_pow₀ (by norm_num) (by omega)
    linarith
  have hA : (∏ i ∈ Finset.range j, ((2 : ℚ) ^ (r + j - i) - 1)) =
      ∏ s ∈ Finset.range j, ((2 : ℚ) ^ (r + 1 + s) - 1) := by
    rw [← Finset.prod_range_reflect]
    apply Finset.prod_congr rfl
    intro s hs
    rw [Finset.mem_range] at hs
    congr 2
    omega
  have hB : (∏ i ∈ Finset.range (r + j), ((2 : ℚ) ^ (2 * (r + j) - j - i) - 1)) =
      ∏ s ∈ Finset.range (r + j), ((2 : ℚ) ^ (r + 1 + s) - 1) := by
    rw [← Finset.prod_range_reflect]
    apply Finset.prod_congr rfl
    intro s hs
    rw [Finset.mem_range] at hs
    congr 2
    omega
  have hP : (∏ i ∈ Finset.range (r + j), ((2 : ℚ) ^ (i + 1) - 1)) =
      (∏ i ∈ Finset.range r, ((2 : ℚ) ^ (i + 1) - 1)) * ∏ s ∈ Finset.range j, ((2 : ℚ) ^ (r + 1 + s) - 1) := by
    rw [Finset.prod_range_add]
    congr 1
    apply Finset.prod_congr rfl
    intro s _
    congr 2
    omega
  have hLow : (∏ i ∈ Finset.range j, ((2 : ℚ) ^ j - 2 ^ i)) =
      2 ^ (j * (j - 1) / 2) * ∏ s ∈ Finset.range j, ((2 : ℚ) ^ (s + 1) - 1) := by
    have h1 : ∀ i ∈ Finset.range j, ((2 : ℚ) ^ j - 2 ^ i) = 2 ^ i * (2 ^ (j - i) - 1) := by
      intro i hi
      rw [Finset.mem_range] at hi
      rw [mul_sub, ← pow_add, Nat.add_sub_cancel' hi.le, mul_one]
    rw [Finset.prod_congr rfl h1, Finset.prod_mul_distrib, Finset.prod_pow_eq_pow_sum, Finset.sum_range_id]
    congr 1
    rw [← Finset.prod_range_reflect]
    apply Finset.prod_congr rfl
    intro s hs
    rw [Finset.mem_range] at hs
    congr 2
    omega
  have hHigh : ∀ (a c : ℕ), (∏ t ∈ Finset.range c, ((2 : ℚ) ^ j - 2 ^ (j + a + t))) =
      (-1) ^ c * 2 ^ (j * c) * ∏ t ∈ Finset.range c, ((2 : ℚ) ^ (a + t) - 1) := by
    intro a c
    have h1 : ∀ t ∈ Finset.range c, ((2 : ℚ) ^ j - 2 ^ (j + a + t)) = (-1) * 2 ^ j * (2 ^ (a + t) - 1) := by
      intro t _
      rw [add_assoc, pow_add]
      ring
    rw [Finset.prod_congr rfl h1, Finset.prod_mul_distrib, Finset.prod_mul_distrib, Finset.prod_const,
      Finset.prod_const, Finset.card_range, ← pow_mul]
  -- the excluded-index product splits at j
  have hErase : (∏ i ∈ (Finset.range (r + j + 1)).erase j, ((2 : ℚ) ^ j - 2 ^ i)) =
      (∏ i ∈ Finset.range j, ((2 : ℚ) ^ j - 2 ^ i)) * ∏ t ∈ Finset.range r, ((2 : ℚ) ^ j - 2 ^ (j + 1 + t)) := by
    have hset : (Finset.range (r + j + 1)).erase j = Finset.range j ∪ Finset.Ico (j + 1) (r + j + 1) := by
      ext i
      simp only [Finset.mem_erase, Finset.mem_range, Finset.mem_union, Finset.mem_Ico]
      omega
    have hdisj : Disjoint (Finset.range j) (Finset.Ico (j + 1) (r + j + 1)) := by
      rw [Finset.disjoint_left]
      intro i hi hi'
      simp only [Finset.mem_range, Finset.mem_Ico] at hi hi'
      omega
    rw [hset, Finset.prod_union hdisj, Finset.prod_Ico_eq_prod_range]
    congr 1
    have : r + j + 1 - (j + 1) = r := by omega
    rw [this]
  have hRHS : (∏ m ∈ Finset.Ico (r + j + 1) (2 * (r + j) + 1), ((2 : ℚ) ^ j - 2 ^ m)) =
      ∏ t ∈ Finset.range (r + j), ((2 : ℚ) ^ j - 2 ^ (j + (r + 1) + t)) := by
    rw [Finset.prod_Ico_eq_prod_range]
    have : 2 * (r + j) + 1 - (r + j + 1) = r + j := by omega
    rw [this]
    apply Finset.prod_congr rfl
    intro t _
    congr 2
    omega
  have hXne : (∏ s ∈ Finset.range j, ((2 : ℚ) ^ (r + 1 + s) - 1)) ≠ 0 := by
    rw [Finset.prod_ne_zero_iff]
    intro i _
    have : (1 : ℚ) < 2 ^ (r + 1 + i) := one_lt_pow₀ (by norm_num) (by omega)
    linarith
  have hH1 := hHigh 1 r
  have hH1' : (∏ t ∈ Finset.range r, ((2 : ℚ) ^ (1 + t) - 1)) = ∏ t ∈ Finset.range r, ((2 : ℚ) ^ (t + 1) - 1) := by
    apply Finset.prod_congr rfl
    intro t _
    rw [add_comm]
  have hH2 := hHigh (r + 1) (r + j)
  have hexp : (2 : ℚ) ^ (j * (j - 1) / 2) * 2 ^ (j * (j - 1) / 2) * 2 ^ j * 2 ^ (j * r) = 2 ^ (j * (r + j)) := by
    rw [← pow_add, ← pow_add, ← pow_add]
    congr 1
    have h2 : j * (j - 1) / 2 * 2 = j * (j - 1) := Nat.div_mul_cancel (Nat.even_mul_pred_self j).two_dvd
    rcases j with _ | i
    · simp
    · simp only [Nat.add_sub_cancel] at h2 ⊢
      nlinarith [h2]
  rw [Finset.prod_div_distrib, Finset.prod_div_distrib, hA, hB, hP, hErase, hLow, hH1, hH1', hRHS, hH2]
  rw [← hexp, pow_add]
  have h1 := hPne j
  have h2 := hPne r
  field_simp
