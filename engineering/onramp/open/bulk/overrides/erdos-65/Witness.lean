/-! Non-vacuity witness (D-4 step 7): the complete bipartite graph K_{1,1} on Unit ⊕ Unit, taken as both graphs, with n = 2 and k = (its number of edges)/2, which is positive since it has an edge. -/

theorem witness : ∃ (k : ℝ) (n : ℕ) (V : Type) (inst : Fintype V) (G : SimpleGraph V) (A : Type) (B : Type) (inst_1 : Fintype A) (inst_2 :
  Fintype B),
  (0 : ℝ) < k ∧
    (0 : ℕ) < n ∧
      Fintype.card V = n ∧
        (↑G.edgeSet.ncard : ℝ) = k * (↑n : ℝ) ∧
          Fintype.card (A ⊕ B) = n ∧ (↑(completeBipartiteGraph A B).edgeSet.ncard : ℝ) = k * (↑n : ℝ) := by
  have hne : (completeBipartiteGraph Unit Unit).edgeSet.Nonempty :=
    ⟨s(Sum.inl (), Sum.inr ()), by simp⟩
  have hpos : 0 < (completeBipartiteGraph Unit Unit).edgeSet.ncard :=
    (Set.ncard_pos (Set.toFinite _)).mpr hne
  refine ⟨((completeBipartiteGraph Unit Unit).edgeSet.ncard : ℝ) / 2, 2, Unit ⊕ Unit, inferInstance,
    completeBipartiteGraph Unit Unit, Unit, Unit, inferInstance, inferInstance, ?_, by norm_num, by simp, ?_, by simp, ?_⟩
  · exact div_pos (by exact_mod_cast hpos) two_pos
  · exact (div_mul_cancel₀ _ two_ne_zero).symm
  · exact (div_mul_cancel₀ _ two_ne_zero).symm
