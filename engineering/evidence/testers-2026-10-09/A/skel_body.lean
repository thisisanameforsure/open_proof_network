  have hall : (∃ K₁ : ℕ, ∀ n k : ℕ, K₁ < k → 2 * k ≤ n → n < k * k → k % 2 = 0 →
        ∃ p : ℕ, Nat.Prime p ∧ p ≤ k ∧ n % p < k % p) ∧
      (∃ K₂ : ℕ, ∀ n k : ℕ, K₂ < k → 2 * k ≤ n → n < k * k → k % 2 = 1 → n % 2 = 1 →
        ∃ p : ℕ, Nat.Prime p ∧ p ≤ k ∧ n % p < k % p) := by
    refine ⟨?_, ?_⟩
    · have h_keven : ∃ K₁ : ℕ, ∀ n k : ℕ, K₁ < k → 2 * k ≤ n → n < k * k → k % 2 = 0 →
          ∃ p : ℕ, Nat.Prime p ∧ p ≤ k ∧ n % p < k % p := by sorry
      exact h_keven
    · have h_odd : ∃ K₂ : ℕ, ∀ n k : ℕ, K₂ < k → 2 * k ≤ n → n < k * k → k % 2 = 1 → n % 2 = 1 →
          ∃ p : ℕ, Nat.Prime p ∧ p ≤ k ∧ n % p < k % p := by sorry
      exact h_odd
  obtain ⟨K₁, h₁⟩ := hall.1
  obtain ⟨K₂, h₂⟩ := hall.2
  refine ⟨max K₁ (max K₂ 1), fun n k hk h2k hnk => ?_⟩
  have hK₁ : K₁ < k := lt_of_le_of_lt (le_max_left _ _) hk
  have hK₂ : K₂ < k := lt_of_le_of_lt (le_trans (le_max_left _ _) (le_max_right _ _)) hk
  have hk1 : 1 < k := lt_of_le_of_lt (le_trans (le_max_right K₂ 1) (le_max_right _ _)) hk
  rcases Nat.mod_two_eq_zero_or_one k with hk2 | hk2
  · exact h₁ n k hK₁ h2k hnk hk2
  · rcases Nat.mod_two_eq_zero_or_one n with hn2 | hn2
    · exact ⟨2, Nat.prime_two, hk1, by omega⟩
    · exact h₂ n k hK₂ h2k hnk hk2 hn2
