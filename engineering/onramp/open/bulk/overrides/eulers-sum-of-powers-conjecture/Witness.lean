/-! Non-vacuity witness (D-4 step 7): sixty-four sixth powers of 1 sum to 2^6, with n = 64 > 1 and k = 6 > 5. -/

theorem witness : ∃ (n : ℕ) (k : ℕ) (b : ℕ) (a : Fin n → ℕ),
  (1 : ℕ) < n ∧ (5 : ℕ) < k ∧ (∀ (i : Fin n), a i > (0 : ℕ)) ∧ ∑ i : Fin n, a i ^ k = b ^ k :=
  ⟨64, 6, 2, fun _ => 1, by norm_num, by norm_num, fun _ => Nat.one_pos, by simp⟩
