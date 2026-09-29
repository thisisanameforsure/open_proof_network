import Mathlib

theorem witness : ∃ A : Finset ℕ, 0 ∉ A ∧ A.card = 12 := ⟨Finset.Icc 1 12, by decide, by decide⟩
