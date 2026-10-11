theorem screen_neg : ¬ conj := by
  intro h
  have h1 := h 1 trivial
  have e : (fun k : ℕ ↦ ((iter 1 k : ℕ) : ℝ) ^ (1 / (k : ℝ))) = fun _ => 1 := by
    funext k
    have : iter 1 k = 1 := by
      unfold iter
      induction k with
      | zero => rfl
      | succ k ih => rw [Function.iterate_succ_apply', ih]; decide
    simp [this]
  rw [e] at h1
  exact Filter.not_tendsto_const_atTop 1 _ h1
