/-! Non-vacuity witness (D-4 step 7): k = 1, m = 3 are positive and 1 + 2 = 3, the one known solution of the Erdős–Moser equation. -/

theorem witness : ∃ (k m : ℕ), 0 < k ∧ 0 < m ∧ ErdosMoser.powerSum k m = m ^ k :=
  ⟨1, 3, one_pos, by norm_num, by decide⟩
