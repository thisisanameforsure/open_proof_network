import Mathlib

/-- Erdős 849 read literally: for every t ≥ 1 some a has exactly t solutions (n, k) of
C(n, k) = a with 1 ≤ k ≤ n/2, counted as pairs, with `encard` so an infinite solution set
is never mistaken for a finite count. -/
theorem claim : ∀ t : ℕ, 1 ≤ t → ∃ a : ℕ,
    {p : ℕ × ℕ | 1 ≤ p.2 ∧ 2 * p.2 ≤ p.1 ∧ Nat.choose p.1 p.2 = a}.encard = t := by
  sorry
