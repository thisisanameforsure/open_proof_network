import Mathlib

-- Audit (D): B's partial on erdos-68--h6, precheck 01M64264AGV6E9DBS1TYP8Q3KE, graph 4f771bb8ad.
-- h1: have ↔ printed closed_type
example : ( ∀ M : ℕ, ∃ N : ℕ, M ≤ N ∧
      Int.fract (∑ n ∈ Finset.Icc (2 : ℕ) N, (↑N.factorial : ℝ) / ((↑n.factorial : ℝ) - (1 : ℝ))) ≤ (1 : ℝ) - (1 : ℝ) / (↑N : ℝ) ) ↔
  (∀ (M : ℕ),
  ∃ (N : ℕ),
    M ≤ N ∧
      Int.fract (∑ n ∈ Finset.Icc (2 : ℕ) N, (↑N.factorial : ℝ) / ((↑n.factorial : ℝ) - (1 : ℝ))) ≤
        (1 : ℝ) - (1 : ℝ) / (↑N : ℝ)) := Iff.rfl
-- h1 is exactly h6's first disjunct, and it implies h6
example : (∀ (M : ℕ),
  ∃ (N : ℕ),
    M ≤ N ∧
      Int.fract (∑ n ∈ Finset.Icc (2 : ℕ) N, (↑N.factorial : ℝ) / ((↑n.factorial : ℝ) - (1 : ℝ))) ≤
        (1 : ℝ) - (1 : ℝ) / (↑N : ℝ)) →
  ∀ (M : ℕ), ∃ (N : ℕ), M ≤ N ∧ (Int.fract (∑ n ∈ Finset.Icc (2 : ℕ) N, (↑N.factorial : ℝ) / ((↑n.factorial : ℝ) - (1 : ℝ))) ≤ (1 : ℝ) - (1 : ℝ) / (↑N : ℝ) ∨
    (1 : ℝ) - (1 : ℝ) / ((↑N : ℝ) + (1 : ℝ)) ≤ Int.fract (∑ n ∈ Finset.Icc (2 : ℕ) N, (↑N.factorial : ℝ) / ((↑n.factorial : ℝ) - (1 : ℝ)))) :=
  fun h M => (h M).imp fun _ hN => ⟨hN.1, Or.inl hN.2⟩
-- h3 → h1 (so the hole is no stronger than --h3)
example : (∀ (M : ℕ), ∃ (N : ℕ), M ≤ N ∧ Int.fract (∑ n ∈ Finset.Icc (2 : ℕ) N, (↑N.factorial : ℝ) / ((↑n.factorial : ℝ) - (1 : ℝ))) < (1 : ℝ) - (2 : ℝ) / (↑N : ℝ)) → (∀ (M : ℕ),
  ∃ (N : ℕ),
    M ≤ N ∧
      Int.fract (∑ n ∈ Finset.Icc (2 : ℕ) N, (↑N.factorial : ℝ) / ((↑n.factorial : ℝ) - (1 : ℝ))) ≤
        (1 : ℝ) - (1 : ℝ) / (↑N : ℝ)) := by
  intro h M
  obtain ⟨N, hMN, hN⟩ := h M
  refine ⟨N, hMN, le_of_lt (lt_of_lt_of_le hN ?_)⟩
  have : (0 : ℝ) ≤ 1 / (N : ℝ) := by positivity
  have h2 : (2 : ℝ) / N = 2 * (1 / N) := by ring
  linarith
