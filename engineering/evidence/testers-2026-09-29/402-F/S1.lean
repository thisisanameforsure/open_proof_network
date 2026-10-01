import Mathlib

/-! The structure lemma every fixed-size case of Erdős problem 402 (Graham's gcd problem) repeats:
with M the largest element of A, if gcd(M, x) > M/n for every x in A, then every other element
of A is (j/k)·M with 1 ≤ j < k < n. A card-n variant needs it with n = A.card: when some x has
gcd(M, x) ≤ M/n the pair (M, x) already answers, and otherwise every element is one of finitely
many fractions of M, which a finite check finishes. -/

theorem Opn.erdos_402_max_fraction_form :
    ∀ (n : ℕ) (A : Finset ℕ) (hne : A.Nonempty), 0 ∉ A →
      (∀ x ∈ A, A.max' hne < (A.max' hne).gcd x * n) →
      ∀ x ∈ A.erase (A.max' hne), ∃ j k : ℕ, 1 ≤ j ∧ j < k ∧ k < n ∧ k * x = j * A.max' hne := by
  sorry
