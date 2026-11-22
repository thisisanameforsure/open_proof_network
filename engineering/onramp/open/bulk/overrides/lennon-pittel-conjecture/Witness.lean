/-! Non-vacuity witness (D-4 step 7): ε n = 1/(n+1) is positive, antitone and tends to 0. -/

theorem witness : ∃ (ε : ℕ → ℝ), (∀ (n : ℕ), (0 : ℝ) < ε n) ∧ Antitone ε ∧ Filter.Tendsto ε Filter.atTop (nhds (0 : ℝ)) :=
  ⟨fun n => 1 / ((n : ℝ) + 1), fun n => by positivity,
    antitone_nat_of_succ_le (fun n => one_div_le_one_div_of_le (by positivity) (by push_cast; linarith)),
    tendsto_one_div_add_atTop_nhds_zero_nat⟩
