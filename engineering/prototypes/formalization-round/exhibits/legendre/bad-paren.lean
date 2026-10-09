theorem screen : ∀ n, claim n := fun n _ =>
  ⟨0, Nat.pow_pos (Nat.succ_pos n), fun h => absurd h (Nat.not_lt_zero _)⟩
