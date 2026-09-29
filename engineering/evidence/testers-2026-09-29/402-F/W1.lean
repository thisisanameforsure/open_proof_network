import Mathlib

theorem witness : ∃ (n : ℕ) (A : Finset ℕ) (hne : A.Nonempty) (x : ℕ),
    (0 : ℕ) ∉ A ∧ (∀ x ∈ A, A.max' hne < (A.max' hne).gcd x * n) ∧ x ∈ A.erase (A.max' hne) :=
  ⟨3, {1, 2}, ⟨1, by simp⟩, 1, by decide, by decide, by decide⟩
