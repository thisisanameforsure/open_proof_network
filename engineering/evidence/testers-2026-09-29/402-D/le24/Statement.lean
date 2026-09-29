import Mathlib

/-! Graham's gcd conjecture (Erdős problem 402) for every set of at most twenty-four positive
integers. A one-element set is immediate (a = b). For |A| = n ≥ 2 let M be the largest element;
either some x has gcd(M, x) ≤ M/n, or each other element is (j/k)·M with 1 ≤ j < k ≤ n - 1,
and L·x/M, with L = lcm(1..n-1), is one of the finitely many integers L·j/k. For each n up to
24 those integers split into n - 2 classes in which two distinct members c, d always have
n·gcd(c, d) ≤ c or n·gcd(c, d) ≤ d, so two of the n - 1 other elements share a class and
gcd(x, y)·L = gcd(c, d)·M carries the bound back. One argument, a finite certificate per n. -/

theorem Opn.erdos_402_card_le_twenty_four :
    ∀ (A : Finset ℕ), 0 ∉ A → A.Nonempty → A.card ≤ 24 →
      ∃ a ∈ A, ∃ b ∈ A, a.gcd b ≤ (a / A.card : ℚ) := by
  sorry
