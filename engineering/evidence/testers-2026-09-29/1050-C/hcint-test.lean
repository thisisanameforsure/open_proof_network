import Mathlib

theorem hcint_test : ∀ (Qc : ℕ → ℕ → ℚ),
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
            ∀ (n : ℕ) (M : ℕ → ℕ),
              (M = fun (n : ℕ) => ∏ m ∈ Finset.Ioc (n / (2 : ℕ)) n, ((2 : ℕ) ^ m - (1 : ℕ))) →
                ∀ (C : ℕ → ℕ),
                  (C = fun (n : ℕ) => ∏ j ∈ Finset.Ico (2 : ℕ) n, ((2 : ℕ) ^ (j + (1 : ℕ)) - (3 : ℕ))) →
                    (∀ k ≤ n, ∃ (z : ℤ), (↑z : ℚ) * (2 : ℚ) ^ (k * (k - (1 : ℕ)) / (2 : ℕ)) = Qc n k) →
                      (∀ k ≤ n,
                          ∃ (z : ℤ),
                            (↑z : ℚ) * (2 : ℚ) ^ (k * (k - (1 : ℕ)) / (2 : ℕ)) =
                              (↑(M n) : ℚ) * ∑ j ∈ Finset.range (k + (1 : ℕ)), Qc n j / ((2 : ℚ) ^ (k - j) - (1 : ℚ))) →
                        ∃ (z : ℤ),
                          (↑z : ℚ) = (↑(C n) : ℚ) * ∑ j ∈ Finset.range n, (3 : ℚ) / ((2 : ℚ) ^ (j + (1 : ℕ)) - (3 : ℚ)) := by
  intro Qc _ Qx _ Aq _ n M _ C hC _ _
  subst hC
  simp only []
  set P : ℕ := ∏ j ∈ Finset.Ico 2 n, (2 ^ (j + 1) - 3) with hP
  rw [Finset.mul_sum]
  refine Finset.sum_induction _ (fun q : ℚ => ∃ z : ℤ, (z : ℚ) = q)
    (fun x y ⟨zx, hx⟩ ⟨zy, hy⟩ => ⟨zx + zy, by push_cast; rw [hx, hy]⟩) ⟨0, by simp⟩ ?_
  intro j hj
  have hjn := Finset.mem_range.mp hj
  rcases Nat.lt_or_ge j 2 with hj2 | hj2
  · interval_cases j
    · exact ⟨-3 * (P : ℤ), by push_cast; norm_num; ring⟩
    · exact ⟨3 * (P : ℤ), by push_cast; norm_num; ring⟩
  · have hdvd : (2 ^ (j + 1) - 3) ∣ P :=
      Finset.dvd_prod_of_mem (fun j => 2 ^ (j + 1) - 3) (Finset.mem_Ico.mpr ⟨hj2, hjn⟩)
    obtain ⟨R, hR⟩ := hdvd
    have h8 : 8 ≤ 2 ^ (j + 1) := by
      calc 8 = 2 ^ 3 := by norm_num
        _ ≤ 2 ^ (j + 1) := Nat.pow_le_pow_right (by norm_num) (by omega)
    have hcast : ((2 ^ (j + 1) - 3 : ℕ) : ℚ) = (2 : ℚ) ^ (j + 1) - 3 := by
      rw [Nat.cast_sub (by omega)]; push_cast; ring
    have hne : (2 : ℚ) ^ (j + 1) - 3 ≠ 0 := by
      rw [← hcast]; exact_mod_cast (by omega : 2 ^ (j + 1) - 3 ≠ 0)
    refine ⟨3 * (R : ℤ), ?_⟩
    rw [hR, Nat.cast_mul, hcast]
    push_cast
    field_simp
