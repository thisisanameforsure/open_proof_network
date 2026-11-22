/-! Non-vacuity witness (D-4 step 7): Bool × Bool under the product order is a finite poset that is not total ((true, false) and (false, true) are incomparable), and total_ext is defined as exactly the set the membership condition describes. -/

theorem witness : ∃ (P : Type) (inst : PartialOrder P) (total_ext : Set (P →o ℕ)),
  Finite P ∧
    (¬Std.Total fun (x1 x2 : P) => x1 ≤ x2) ∧
      ∀ (σ : P →o ℕ), σ ∈ total_ext ↔ Set.range (⇑σ : P → ℕ) = Set.Icc (1 : ℕ) (Nat.card P) :=
  ⟨Bool × Bool, inferInstance, {σ | Set.range (⇑σ : Bool × Bool → ℕ) = Set.Icc (1 : ℕ) (Nat.card (Bool × Bool))},
    inferInstance,
    fun h => by
      have := h.total (true, false) (false, true)
      simp [Prod.le_def, Bool.le_iff_imp] at this,
    fun σ => Iff.rfl⟩
