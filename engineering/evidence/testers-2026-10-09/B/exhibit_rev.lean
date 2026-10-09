import Mathlib

open scoped Nat

theorem rev_exhibit :
    (∃ (K : ℕ), ∀ (n k : ℕ), (0 : ℕ) < k → k * k ≤ n → (n.choose k).minFac > n / k → k ≤ K) →
    (∃ (K : ℕ), ∀ (n k : ℕ), (0 : ℕ) < k → k * k * k ≤ n → (n.choose k).minFac > n / k → k ≤ K) := by
  rintro ⟨K, h⟩
  exact ⟨K, fun n k hk hn hex => h n k hk (le_trans (Nat.le_mul_of_pos_right _ hk) hn) hex⟩
