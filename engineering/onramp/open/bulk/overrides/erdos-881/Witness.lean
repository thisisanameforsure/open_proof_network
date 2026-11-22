/-! Non-vacuity witness (D-4 step 7): ℕ itself is a minimal asymptotic basis of order 1: every number is a one-fold sum from ℕ, and removing an infinite set leaves infinitely many numbers uncovered. (Written unchecked.) -/

theorem witness : ∃ (k : ℕ) (A : Set ℕ), IsMinimalAsymptoticAddBasisOfOrder k A :=
  ⟨1, Set.univ, by
    refine ⟨?_, fun B _ hB h => ?_⟩
    · simp [Set.IsAsymptoticAddBasisOfOrder]
    · simp only [Set.IsAsymptoticAddBasisOfOrder, one_nsmul, Set.univ_diff,
        Filter.eventually_cofinite, Set.mem_compl_iff, not_not] at h
      exact hB (h.subset fun x hx => by simpa using hx)⟩
