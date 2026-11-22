/-! Non-vacuity witness (D-4 step 7): the zero function is additive on coprime arguments, and the set where it decreases is empty, which has density 0. -/

theorem witness : ∃ (f : ℕ → ℝ),
    (∀ a > 0, ∀ b > 0, Nat.Coprime a b → f (a * b) = f a + f b) ∧
      {n | 1 ≤ n ∧ f (n + 1) < f n}.HasDensity 0 := by
  refine ⟨fun _ => 0, fun a _ b _ _ => by simp, ?_⟩
  have h : {n : ℕ | 1 ≤ n ∧ (fun _ : ℕ => (0 : ℝ)) (n + 1) < (fun _ : ℕ => (0 : ℝ)) n} = ∅ := by
    ext n; simp
  rw [h]
  simp [Set.HasDensity, Set.partialDensity]
