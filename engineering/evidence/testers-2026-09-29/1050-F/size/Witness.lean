import Mathlib

theorem witness : ∃ (n : ℕ), n ≠ 5 ∧ n ≠ 7 := ⟨0, by decide, by decide⟩
