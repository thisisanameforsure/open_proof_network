/-! Non-vacuity witness (D-4 step 7): A = ℕ itself; every n is n + 0, so the complement of A + A is empty. -/

theorem witness : ∃ (A : Set ℕ), (A + A)ᶜ.Finite :=
  ⟨Set.univ, Set.finite_empty.subset fun n hn =>
    (hn (Set.mem_add.mpr ⟨n, Set.mem_univ _, 0, Set.mem_univ _, add_zero n⟩)).elim⟩
