import Mathlib

theorem witness : ∃ (n : ℕ) (k : ℕ) (c : ℕ → ℤ), k ≤ n := ⟨0, 0, fun _ => 0, le_refl 0⟩
