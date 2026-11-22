/-! Non-vacuity witness (D-4 step 7): the constant sequence d n = 1 is at least 1 and d n / n tends to 0. -/

theorem witness : ∃ (d : ℕ → ℕ), (∀ (n : ℕ), (1 : ℕ) ≤ d n) ∧ Filter.Tendsto (fun (n : ℕ) => (↑(d n) : ℝ) / (↑n : ℝ)) Filter.atTop (nhds (0 : ℝ)) :=
  ⟨fun _ => 1, fun _ => le_refl 1, by simpa using tendsto_one_div_atTop_nhds_zero_nat⟩
