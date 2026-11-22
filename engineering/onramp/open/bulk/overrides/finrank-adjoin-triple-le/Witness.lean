/-! Non-vacuity witness (D-4 step 7): over ℚ, the three zero 0×0 matrices commute pairwise. -/

theorem witness : ∃ (K : Type _) (inst : Field K) (n : ℕ) (A B C : Matrix (Fin n) (Fin n) K),
    ({A, B, C} : Set (Matrix (Fin n) (Fin n) K)).Pairwise Commute :=
  ⟨ℚ, inferInstance, 0, 0, 0, 0, fun x hx y hy _ => by
    simp only [Set.mem_insert_iff, Set.mem_singleton_iff, or_self] at hx hy
    subst hx; subst hy; exact Commute.refl 0⟩
