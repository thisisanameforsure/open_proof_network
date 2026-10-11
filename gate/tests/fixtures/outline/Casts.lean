/-! F19-AC3: a claim over the integers with natural-number casts (the 2026-09-17 shape, in Lean
core, where there are no reals), and a claim that names an inaccessible local, which no printer
can make read back. -/

theorem OpnOutline.casts (n : Nat) : (n : Int) - 5 < (n : Int) + 1 := by
  have hc : (n : Int) - 5 < (n : Int) := by omega
  omega

theorem OpnOutline.hidden : ∀ n : Nat, n + 0 = n := by
  intro
  have e : ‹Nat› + 0 = ‹Nat› := rfl
  exact e
