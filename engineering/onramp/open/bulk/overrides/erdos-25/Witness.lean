/-! Non-vacuity witness (D-4 step 7): the moduli n_i = i + 1 are positive and strictly increasing, with every residue 0. -/

theorem witness : ∃ (seq_n : ℕ → ℕ) (seq_a : ℕ → ℤ), (∀ (i : ℕ), (0 : ℕ) < seq_n i) ∧ StrictMono seq_n :=
  ⟨fun i => i + 1, fun _ => 0, fun i => Nat.succ_pos i, fun a b h => Nat.succ_lt_succ h⟩
