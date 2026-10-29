import Mathlib

theorem Opn.erdos_68 :
    Irrational (∑' n : ℕ, 1 / ((n + 2).factorial - 1 : ℝ)) := by
  have h1 : ∀ x : ℝ, (∀ M : ℕ, ∃ N : ℕ, M ≤ N ∧ ∀ m : ℤ, (N.factorial : ℝ) * x ≠ m) →
      Irrational x := sorry
  have h2 : ∀ N : ℕ, 2 ≤ N → ∃ c : ℝ, 0 < c ∧ c ≤ 2 / N ∧
      (N.factorial : ℝ) * (∑' n : ℕ, 1 / ((n + 2).factorial - 1 : ℝ)) =
        (∑ n ∈ Finset.Icc 2 N, (N.factorial : ℝ) / ((n.factorial : ℝ) - 1)) + c := sorry
  have h3 : ∀ M : ℕ, ∃ N : ℕ, M ≤ N ∧
      Int.fract (∑ n ∈ Finset.Icc 2 N, (N.factorial : ℝ) / ((n.factorial : ℝ) - 1)) <
        1 - 2 / N := sorry
  apply h1
  intro M
  obtain ⟨N, hMN, hfr⟩ := h3 (max M 2)
  refine ⟨N, le_trans (le_max_left _ _) hMN, ?_⟩
  intro m hm
  obtain ⟨c, hc0, hc2, hS⟩ := h2 N (le_trans (le_max_right _ _) hMN)
  set F := ∑ n ∈ Finset.Icc 2 N, (N.factorial : ℝ) / ((n.factorial : ℝ) - 1) with hFdef
  have hF : F + c = m := by rw [← hS, hm]
  have h0 : 0 ≤ Int.fract F := Int.fract_nonneg F
  have key : Int.fract F + c = ((m - ⌊F⌋ : ℤ) : ℝ) := by
    rw [Int.fract]; push_cast; linarith
  have hlt : Int.fract F + c < 1 := by linarith
  have hpos : 0 < Int.fract F + c := by linarith
  rw [key] at hlt hpos
  have hlt' : m - ⌊F⌋ < 1 := by exact_mod_cast hlt
  have hpos' : 0 < m - ⌊F⌋ := by exact_mod_cast hpos
  omega
