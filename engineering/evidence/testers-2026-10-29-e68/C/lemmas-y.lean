import Mathlib

/-- y_N = fract(N!·S) obeys y_{N+1} = fract((N+1)·y_N). -/
theorem C_y_rec (S : ℝ) (N : ℕ) :
    Int.fract (((N + 1).factorial : ℝ) * S) =
      Int.fract (((N : ℝ) + 1) * Int.fract ((N.factorial : ℝ) * S)) := by
  have h : ((N + 1).factorial : ℝ) * S = ((N : ℝ) + 1) * Int.fract ((N.factorial : ℝ) * S) +
      (((N + 1 : ℕ) : ℤ) * ⌊(N.factorial : ℝ) * S⌋ : ℤ) := by
    rw [Nat.factorial_succ]; push_cast
    rw [← Int.self_sub_floor]; ring
  rw [h, Int.fract_add_intCast]
