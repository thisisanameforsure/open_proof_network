import Mathlib

theorem witness : ∃ A : Finset ℕ, 0 ∉ A ∧ A.card = 15 := ⟨Finset.Icc 1 15, by decide, by decide⟩
