import Mathlib

theorem witness : ∃ A : Finset ℕ, 0 ∉ A ∧ A.card = 25 :=
  ⟨Finset.Icc 1 25, by decide, by decide⟩
