import Mathlib

theorem witness : ∃ A : Finset ℕ, 0 ∉ A ∧ A.card = 14 :=
  ⟨Finset.Icc 1 14, by simp, by simp⟩
