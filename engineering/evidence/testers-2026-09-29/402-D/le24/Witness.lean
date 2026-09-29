import Mathlib

theorem witness : ∃ A : Finset ℕ, 0 ∉ A ∧ A.Nonempty ∧ A.card ≤ 24 :=
  ⟨{1}, by simp, by simp, by simp⟩
