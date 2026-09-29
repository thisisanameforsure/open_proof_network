import Mathlib

example : True := by
  obtain ⟨cls, hcls⟩ : ∃ cls : ℕ → List ℕ, cls = fun i => [[420, 600], [210, 360, 672, 700],
      [120, 560, 630], [105, 240, 504], [280, 315, 480], [168, 525, 720], [140, 336, 735]].getD i [] :=
    ⟨_, rfl⟩
  obtain ⟨col, hcol⟩ : ∃ col : ℕ → ℕ, col = fun c => [[420, 600], [210, 360, 672, 700],
      [120, 560, 630], [105, 240, 504], [280, 315, 480], [168, 525, 720], [140, 336, 735]].findIdx
      (fun C => C.contains c) := ⟨_, rfl⟩
  have F1 : ∀ c ∈ ([105, 120, 140, 168, 210, 240, 280, 315, 336, 360, 420, 480, 504, 525, 560,
      600, 630, 672, 700, 720, 735] : List ℕ), col c < 7 ∧ c ∈ cls (col c) := by
    subst hcol hcls; decide
  have F3 : ∀ i < 7, ∀ c ∈ cls i, ∀ d ∈ cls i, c = d ∨ 9 * c.gcd d ≤ c ∨ 9 * c.gcd d ≤ d := by
    subst hcls; decide
  trivial
