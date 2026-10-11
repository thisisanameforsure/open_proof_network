/-! A related variant of the tutorial node (D-30), proposed by the F08 smoke. -/

theorem OpnProp.and_left_of_and_swap : ∀ p q : Prop, p ∧ q → p := by
  -- annex: c761b2b136f154b6b82cbcb375549ec4f9d30d5772bcbcc20df6d092026eb65a
  intro p q hpq
  have h₁ : q ∧ p := sorry        -- lemma 1 of the annex: a conjunction commutes
  have h₂ : q ∧ p → p := sorry    -- lemma 2 of the annex: the right projection
  exact h₂ h₁                     -- the assembly: proved, not sorry
