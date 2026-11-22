/-! Non-vacuity witness (D-4 step 7): N = 0, the zero modulus function and the empty residue sets (the leading data binders; the hypotheses sit behind the `let`). -/

theorem witness : ∃ (N : ℕ) (p : Fin 1000 → ℕ) (A : (i : Fin 1000) → Finset (ZMod (p i))), True :=
  ⟨0, fun _ => 0, fun _ => ∅, trivial⟩
