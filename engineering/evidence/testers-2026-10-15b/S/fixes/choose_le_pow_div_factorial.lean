lemma choose_le_pow_div_factorial (n j : ℕ) :
    (Nat.choose n j : ℝ) ≤ (n : ℝ) ^ j / (Nat.factorial j : ℝ) := by
  rw [ le_div_iff₀ ( by positivity ) ];
  rw_mod_cast [ mul_comm, ← Nat.descFactorial_eq_factorial_mul_choose ] ; exact Nat.descFactorial_le_pow n j;