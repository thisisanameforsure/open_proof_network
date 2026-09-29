import Mathlib

theorem guess_hcint : ∀ (Qc : ℕ → ℕ → ℚ),
  (Qc = fun (n k : ℕ) =>
      ((-1 : ℚ) ^ k * (2 : ℚ) ^ (k * (k - (1 : ℕ)) / (2 : ℕ)) *
          ∏ i ∈ Finset.range k, ((2 : ℚ) ^ (n - i) - (1 : ℚ)) / ((2 : ℚ) ^ (i + (1 : ℕ)) - (1 : ℚ))) *
        ∏ i ∈ Finset.range n, ((2 : ℚ) ^ ((2 : ℕ) * n - k - i) - (1 : ℚ)) / ((2 : ℚ) ^ (i + (1 : ℕ)) - (1 : ℚ))) →
    ∀ (Qx : ℕ → ℚ),
      (Qx = fun (n : ℕ) => ∑ k ∈ Finset.range (n + (1 : ℕ)), Qc n k * ((3 : ℚ) / (2 : ℚ) ^ n) ^ k) →
        ∀ (Aq : ℕ → ℚ),
          (Aq = fun (n : ℕ) =>
              ∑ k ∈ Finset.range (n + (1 : ℕ)),
                  (∑ j ∈ Finset.range (k + (1 : ℕ)), Qc n j / ((2 : ℚ) ^ (k - j) - (1 : ℚ))) *
                    ((3 : ℚ) / (2 : ℚ) ^ n) ^ k +
                Qx n * ∑ j ∈ Finset.range n, (3 : ℚ) / ((2 : ℚ) ^ (j + (1 : ℕ)) - (3 : ℚ))) →
            ∀ (n : ℕ) (M : ℕ → ℕ), M = (fun n => ∏ m ∈ Finset.Ioc (n / 2) n, (2 ^ m - 1)) →
              ∀ (C : ℕ → ℕ), C = (fun n => ∏ j ∈ Finset.Ico 2 n, (2 ^ (j + 1) - 3)) →
                (∀ k ≤ n, ∃ z : ℤ, (z : ℚ) * (2 : ℚ) ^ (k * (k - 1) / 2) = Qc n k) →
                (∀ k ≤ n, ∃ z : ℤ, (z : ℚ) * (2 : ℚ) ^ (k * (k - 1) / 2) =
                    (M n : ℚ) * ∑ j ∈ Finset.range (k + 1), Qc n j / ((2 : ℚ) ^ (k - j) - 1)) →
                ∃ z : ℤ, (z : ℚ) = (C n : ℚ) * ∑ j ∈ Finset.range n, (3 : ℚ) / ((2 : ℚ) ^ (j + 1) - 3) := by
  have key : ∀ n : ℕ, ∃ z : ℤ, (z : ℚ) = (∏ j ∈ Finset.Ico 2 n, ((2 : ℚ) ^ (j + 1) - 3)) *
      ∑ j ∈ Finset.range n, (3 : ℚ) / ((2 : ℚ) ^ (j + 1) - 3) := by
    intro n
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
  intros
  subst_vars
  obtain ⟨z, hz⟩ := key ‹ℕ›
  refine ⟨z, ?_⟩
  rw [hz]
  congr 1
  push_cast [Nat.cast_prod]
  apply Finset.prod_congr rfl
  intro j hj
  have h3 : 3 ≤ 2 ^ (j + 1) := by
    have : 2 ^ 2 ≤ 2 ^ (j + 1) := Nat.pow_le_pow_right (by norm_num) (by simp at hj; omega)
    omega
  rw [Nat.cast_sub h3]
  push_cast
  ring
