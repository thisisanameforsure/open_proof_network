-- relation: refutes
import Mathlib

/-! The variant refutes the root (D-30, `refutes`): an infinite set whose Mersenne reciprocal
sum is `1/2` is an infinite set whose sum is rational. -/

theorem relation :
    (∃ A : Set ℕ, A.Infinite ∧ ∑' n : A, (1 : ℝ) / (2 ^ n.1 - 1) = 1 / 2) →
    ¬ (∀ (A : Set ℕ), A.Infinite → Irrational (∑' n : A, (1 : ℝ) / (2 ^ n.1 - 1))) := by
  rintro ⟨A, hA, hsum⟩ h
  have hirr := h A hA
  rw [hsum] at hirr
  exact hirr ⟨(1 / 2 : ℚ), by norm_num⟩
