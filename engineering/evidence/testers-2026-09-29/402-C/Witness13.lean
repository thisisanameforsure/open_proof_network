import Mathlib

theorem witness : ∃ A : Finset ℕ, 0 ∉ A ∧ A.card = 13 :=
  ⟨Finset.Icc 1 13, by simp, by simp⟩
