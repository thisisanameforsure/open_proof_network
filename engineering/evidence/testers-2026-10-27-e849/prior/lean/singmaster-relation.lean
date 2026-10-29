import Mathlib

theorem relation :
    (∃ B : ℕ, ∀ a : ℕ,
      {n : ℕ | ∃ k ≥ 1, 2 * k ≤ n ∧ Nat.choose n k = a}.ncard ≤ B) →
    ¬ (∀ t ≥ 1, ∃ a : ℕ,
      {n : ℕ | ∃ k ≥ 1, 2 * k ≤ n ∧ Nat.choose n k = a}.ncard = t) := by
  rintro ⟨B, hB⟩ h
  obtain ⟨a, ha⟩ := h (B + 1) (by omega)
  have hle := hB a
  omega
