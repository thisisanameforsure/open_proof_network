/-! Non-vacuity witness (D-4 step 7): the Latin square of order 1 (one cell holding the symbol 0); 1 is odd. -/

theorem witness : ∃ (n : ℕ) (L : LatinSquare n), Odd n :=
  ⟨1, ⟨fun _ _ => 0, fun _ a b _ => Subsingleton.elim a b, fun _ a b _ => Subsingleton.elim a b⟩,
    odd_one⟩
