import Mathlib

theorem Opn.h1_test : ∀ r : ℕ → ℝ, r 0 = 1 / 2 →
      (∀ m, r (m + 1) = if (1 : ℝ) / (2 ^ m - 1) ≤ r m then r m - 1 / (2 ^ m - 1) else r m) →
      ∀ m, 0 ≤ r m ∧
        ∑ a ∈ Finset.range m, (if (1 : ℝ) / (2 ^ a - 1) ≤ r a then (1 : ℝ) / (2 ^ a - 1) else 0)
          = 1 / 2 - r m := by
  intro r hr0 hrs m
  induction m with
  | zero => simp [hr0]
  | succ m ih =>
    obtain ⟨ihnn, ihsum⟩ := ih
    rw [Finset.sum_range_succ, ihsum, hrs m]
    split_ifs with h
    · exact ⟨by linarith, by ring⟩
    · exact ⟨ihnn, by ring⟩
