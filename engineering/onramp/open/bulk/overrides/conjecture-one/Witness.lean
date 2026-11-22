/-! Non-vacuity witness (D-4 step 7): the empty family of points (n = 0) is injective. -/

theorem witness : ∃ (n : ℕ) (x : Fin n → AtiyahSutcliffe.Point), Function.Injective x :=
  ⟨0, Fin.elim0, fun i => i.elim0⟩
