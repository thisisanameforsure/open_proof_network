lemma int_sq_norm_eq_real_sq_norm (s : ℕ) (x : Fin s → ℤ) :
    (int_sq_norm s x : ℝ) = ∑ i : Fin s, ((x i : ℤ) : ℝ) ^ 2 := by
  unfold int_sq_norm;
  norm_num [ ← @Int.cast_inj ℝ ]