/-! Non-vacuity witness (D-4 step 7): the one-state automaton over a one-letter alphabet is synchronized by the empty word. -/

theorem witness : ∃ (α : Type) (σ : Type) (inst : Fintype σ) (M : DFA α σ), M.IsSynchronizing :=
  ⟨Unit, Unit, inferInstance, ⟨fun _ _ => (), (), Set.univ⟩, ⟨[], (), fun _ => rfl⟩⟩
