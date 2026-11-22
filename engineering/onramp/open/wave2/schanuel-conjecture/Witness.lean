/-! Non-vacuity witness (D-4 step 7): the statement binds `n`, `z : Fin n → ℂ` and
`h : LinearIndependent ℚ z` before its colon, so the expected witness type is the data closed
over the hypothesis; the empty family is linearly independent. Checked against the gate's own
expected type on the hosted checker before import (F14-T18). -/

theorem witness : ∃ (n : ℕ) (z : Fin n → ℂ), LinearIndependent ℚ z :=
  ⟨0, Fin.elim0, linearIndependent_empty_type⟩
