lemma two_mul_r_le_eight_pow (r : ℕ) (hr : 2 ≤ r) :
    2 * (r : ℝ) ≤ (8 : ℝ) ^ (r - 1) := by
  rcases r with ( _ | _ | r ) <;> norm_num at *;
  exact mod_cast Nat.recOn r ( by norm_num ) fun n ihn => by norm_num [ Nat.pow_succ ] at ihn ⊢ ; linarith;