/-! Non-vacuity witness (D-4 step 7): the hypothesis `p ∧ q` is satisfiable. -/

theorem witness : ∃ p q : Prop, p ∧ q := ⟨True, True, trivial, trivial⟩
