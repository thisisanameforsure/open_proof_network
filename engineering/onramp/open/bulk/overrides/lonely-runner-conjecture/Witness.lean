/-! Non-vacuity witness (D-4 step 7): one runner at speed 0, with `lonely` defined as the statement's own clause, so `lonely_def` holds by reflexivity. -/

theorem witness : ∃ (n : ℕ) (speed : Fin n ↪ ℝ) (lonely : Fin n → ℝ → Prop) (r : Fin n),
    ∀ (r : Fin n) (t : ℝ), lonely r t ↔
      ∀ (r2 : Fin n), r2 ≠ r → dist (t * speed r : UnitAddCircle) (t * speed r2) ≥ 1 / n :=
  ⟨1, ⟨fun _ => 0, fun a b _ => Subsingleton.elim a b⟩,
   fun r t => ∀ (r2 : Fin 1), r2 ≠ r → dist (t * 0 : UnitAddCircle) (t * 0) ≥ 1 / (1 : ℕ),
   0, fun _ _ => Iff.rfl⟩
