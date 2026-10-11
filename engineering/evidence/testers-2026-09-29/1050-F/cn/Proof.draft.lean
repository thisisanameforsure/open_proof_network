import Mathlib

/-- erdos-1050, hole hden (erdos-1050--h1-v2--h3): the last term of `Aq` in h3 is
Qx n * c_n with c_n = ∑_{j < n} 3 / (2^(j+1) - 3). Its denominators are 2 - 3 = -1, 4 - 3 = 1 and
2^(j+1) - 3 for 2 ≤ j < n, so the factor ∏_{2 ≤ j < n} (2^(j+1) - 3) of the annex's candidate D_n
(annex 4670684d2f0d on h3; size bound spec-10c6e2b9) clears c_n. With spec-938d7dd3 (the power of 2
clears Qx n) this settles the Qx n * c_n part of D_n * Aq n. -/
theorem erdos_1050_hden_cn_clears (n : ℕ) :
    ∃ z : ℤ, (z : ℚ) = (∏ j ∈ Finset.Ico 2 n, ((2 : ℚ) ^ (j + 1) - 3)) *
      ∑ j ∈ Finset.range n, (3 : ℚ) / ((2 : ℚ) ^ (j + 1) - 3) := by
  have hdvd : ∀ j : ℕ, j < n →
      ((2 : ℤ) ^ (j + 1) - 3) ∣ ∏ i ∈ Finset.Ico 2 n, ((2 : ℤ) ^ (i + 1) - 3) := by
    intro j hj
    rcases Nat.lt_or_ge j 2 with h2 | h2
    · interval_cases j
      · exact ⟨-(∏ i ∈ Finset.Ico 2 n, ((2 : ℤ) ^ (i + 1) - 3)), by ring⟩
      · exact ⟨∏ i ∈ Finset.Ico 2 n, ((2 : ℤ) ^ (i + 1) - 3), by ring⟩
    · exact Finset.dvd_prod_of_mem _ (Finset.mem_Ico.2 ⟨h2, hj⟩)
  have hne : ∀ j : ℕ, ((2 : ℤ) ^ (j + 1) - 3) ≠ 0 := by
    intro j h
    have h3 : (2 : ℤ) ^ (j + 1) = 3 := by linarith
    have hev : Even ((2 : ℤ) ^ (j + 1)) := (Int.even_pow.2 ⟨even_two, by omega⟩)
    rw [h3] at hev
    exact absurd hev (by decide)
  refine ⟨∑ j ∈ Finset.range n,
      3 * ((∏ i ∈ Finset.Ico 2 n, ((2 : ℤ) ^ (i + 1) - 3)) / ((2 : ℤ) ^ (j + 1) - 3)), ?_⟩
  rw [Int.cast_sum, Finset.mul_sum]
  apply Finset.sum_congr rfl
  intro j hj
  rw [Finset.mem_range] at hj
  obtain ⟨q, hq⟩ := hdvd j hj
  have hneq : ((2 : ℚ) ^ (j + 1) - 3) ≠ 0 := by
    have := hne j
    intro h
    apply this
    exact_mod_cast h
  have hP : (∏ i ∈ Finset.Ico 2 n, ((2 : ℚ) ^ (i + 1) - 3)) = ((2 : ℚ) ^ (j + 1) - 3) * (q : ℚ) := by
    have := congrArg (fun z : ℤ => (z : ℚ)) hq
    push_cast at this
    exact this
  rw [hq, Int.mul_ediv_cancel_left _ (hne j), hP]
  push_cast
  field_simp
