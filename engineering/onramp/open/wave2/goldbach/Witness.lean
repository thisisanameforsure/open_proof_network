/-! Non-vacuity witness (D-4 step 7): the statement's leading binder `n` carries the hypotheses
`2 < n` and `Even n`, so the expected witness type is their closure; 4 satisfies both. Checked
against the gate's own expected type on the hosted checker before import (F14-T18). -/

theorem witness : ∃ n : ℕ, 2 < n ∧ Even n := ⟨4, by norm_num, ⟨2, by norm_num⟩⟩
