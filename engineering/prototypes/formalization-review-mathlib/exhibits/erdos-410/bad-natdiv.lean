theorem screen_neg : ¬ conj := by
  intro h
  have h2 := h 2 (by decide)
  have hev : (fun k : ℕ ↦ (iter 2 k : ℝ) ^ ((1 / k : ℕ) : ℝ)) =ᶠ[Filter.atTop] fun _ => 1 := by
    filter_upwards [Filter.eventually_ge_atTop 2] with k hk
    have : (1 / k : ℕ) = 0 := Nat.div_eq_of_lt (by omega)
    simp [this]
  exact Filter.not_tendsto_const_atTop 1 _ ((Filter.tendsto_congr' hev).mp h2)
