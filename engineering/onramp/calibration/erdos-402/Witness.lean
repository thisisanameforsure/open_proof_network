/-! Non-vacuity witness (D-4 step 7): the statement quantifies over a finite set with two hypotheses, so the expected witness type is their closure, an instance of
`∃ A : Finset ℕ, 0 ∉ A ∧ A.Nonempty`. Written by hand (the wave driver refuses binders before the colon) and checked only by the sandboxed admission at intake. -/

theorem witness : ∃ A : Finset ℕ, 0 ∉ A ∧ A.Nonempty :=
  ⟨{1}, by simp, by simp⟩
