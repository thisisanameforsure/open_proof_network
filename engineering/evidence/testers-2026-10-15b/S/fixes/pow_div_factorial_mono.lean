lemma pow_div_factorial_mono {M : ℝ} (hM : 0 ≤ M) {j k : ℕ}
    (hjk : j ≤ k) (hkM : (k : ℝ) ≤ M) :
    M ^ j / (Nat.factorial j : ℝ) ≤ M ^ k / (Nat.factorial k : ℝ) := by
  induction hjk <;> simp_all +decide [ Nat.factorial_succ, pow_succ ];
  rename_i k hk ih;
  exact le_trans ( ih ( by linarith ) ) ( by rw [ div_le_div_iff₀ ] <;> first | positivity | nlinarith [ pow_nonneg hM k, show ( k.factorial : ℝ ) > 0 by positivity, mul_le_mul_of_nonneg_right hkM ( show ( 0 : ℝ ) ≤ M ^ k by positivity ) ] )