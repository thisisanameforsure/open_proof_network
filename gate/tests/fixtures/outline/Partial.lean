/-! F19-AC13: a two-hole partial assembly (D-12), one hole a bare `sorry` and one `by sorry`. -/

theorem OpnOutline.partial (n : Nat) (h : 0 < n) : n ≠ 0 ∧ 1 ≤ n := by
  have h1 : n ≠ 0 := sorry
  have h2 : 1 ≤ n := by sorry
  exact ⟨h1, h2⟩
