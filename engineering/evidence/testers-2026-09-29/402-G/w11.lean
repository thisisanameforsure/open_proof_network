import Mathlib

theorem witness : ∃ A : Finset ℕ, 0 ∉ A ∧ A.card = 11 := ⟨Finset.Icc 1 11, by decide, by decide⟩
