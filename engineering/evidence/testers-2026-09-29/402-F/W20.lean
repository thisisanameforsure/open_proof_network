import Mathlib

theorem witness : ∃ A : Finset ℕ, 0 ∉ A ∧ A.card = 20 :=
  ⟨Finset.Icc 1 20, by decide, by decide⟩
