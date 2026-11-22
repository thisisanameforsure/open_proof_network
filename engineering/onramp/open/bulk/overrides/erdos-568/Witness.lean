/-! Non-vacuity witness (D-4 step 7): the graph on the empty vertex type is contained in every graph, so its Ramsey number against any graph is 0, which is below every positive multiple of n and of n². -/

theorem witness : ∃ (V : Type) (inst : Fintype V) (G : SimpleGraph V),
  (∃ c₁ > (0 : ℝ), ∀ (n : ℕ) (T : SimpleGraph (Fin n)), T.IsTree → (↑(G.graphRamsey T) : ℝ) ≤ c₁ * (↑n : ℝ)) ∧
    ∃ c₂ > (0 : ℝ), ∀ (n : ℕ), (↑(G.graphRamsey (SimpleGraph.completeGraph (Fin n))) : ℝ) ≤ c₂ * (↑n : ℝ) ^ (2 : ℕ) := by
  have h0 : ∀ {β : Type} [Fintype β] (H : SimpleGraph β),
      (⊥ : SimpleGraph Empty).graphRamsey H = 0 := by
    intro β _ H
    refine le_antisymm (Nat.sInf_le ?_) (Nat.zero_le _)
    refine fun C => Or.inl ?_
    first
      | exact ⟨RelEmbedding.ofIsEmpty _ _⟩
      | exact ⟨⟨RelEmbedding.ofIsEmpty _ _⟩⟩
      | exact ⟨(RelEmbedding.ofIsEmpty _ _ : (⊥ : SimpleGraph Empty) ↪g C).toCopy⟩
      | exact ⟨⟨⟨Empty.elim, fun a => a.elim⟩, fun {a} => a.elim⟩⟩
      | exact ⟨⟨⟨Empty.elim, fun {a} => a.elim⟩, fun {a} => a.elim⟩⟩
      | exact ⟨⟨⟨⟨Empty.elim, fun a => a.elim⟩, fun {a} => a.elim⟩⟩⟩
  refine ⟨Empty, inferInstance, ⊥, ⟨1, one_pos, fun n T _ => ?_⟩, ⟨1, one_pos, fun n => ?_⟩⟩
  · rw [h0]; simp only [Nat.cast_zero]; positivity
  · rw [h0]; simp only [Nat.cast_zero]; positivity
