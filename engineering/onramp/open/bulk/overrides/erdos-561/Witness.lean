/-! Non-vacuity witness (D-4 step 7): s = t = 1 with the constant sequences n = m = 1, which are antitone and at least 1. -/

theorem witness : ∃ (s : ℕ) (t : ℕ) (n : Fin s → ℕ) (m : Fin t → ℕ),
    (1 : ℕ) ≤ s ∧ (1 : ℕ) ≤ t ∧ Antitone n ∧ Antitone m ∧
      (∀ (i : Fin s), (1 : ℕ) ≤ n i) ∧ ∀ (j : Fin t), (1 : ℕ) ≤ m j :=
  ⟨1, 1, fun _ => 1, fun _ => 1, le_refl 1, le_refl 1, antitone_const, antitone_const,
   fun _ => le_refl 1, fun _ => le_refl 1⟩
