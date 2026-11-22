/-! Non-vacuity witness (D-4 step 7): two one-vertex graphs, each connected. (The statement leaves `V` auto-bound; the witness binds it as a type.) -/

theorem witness : ∃ (V : Type) (W : Type) (_ : Fintype V) (_ : Fintype W) (_ : DecidableEq W)
    (G : SimpleGraph V) (H : SimpleGraph W), G.Connected ∧ H.Connected :=
  ⟨Unit, Unit, inferInstance, inferInstance, inferInstance, ⊥, ⊥,
   ⟨fun u v => by rw [Subsingleton.elim u v]⟩, ⟨fun u v => by rw [Subsingleton.elim u v]⟩⟩
