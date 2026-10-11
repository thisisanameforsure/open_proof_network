import Mathlib

/-! The certificate for three-element sets: the only fraction (j/k)·M with 1 ≤ j < k < 3 is M/2,
so L = 2, S = {1} and one colour. -/

theorem witness : ∃ (n : ℕ) (L : ℕ) (S : Finset ℕ) (c : ℕ → ℕ) (A : Finset ℕ),
    (2 : ℕ) ≤ n ∧
      (0 : ℕ) < L ∧
        (∀ k ∈ Finset.range n, ∀ j ∈ Finset.range k, (0 : ℕ) < j → k ∣ L * j ∧ L * j / k ∈ S) ∧
          (∀ a ∈ S, c a + (2 : ℕ) < n) ∧
            (∀ a ∈ S, ∀ b ∈ S, a ≠ b → c a = c b → n * a.gcd b ≤ a ∨ n * a.gcd b ≤ b) ∧
              (0 : ℕ) ∉ A ∧ A.card = n :=
  ⟨3, 2, {1}, fun _ => 0, {1, 2, 3}, by decide, by decide, by decide, by decide, by decide,
    by decide, by decide⟩
