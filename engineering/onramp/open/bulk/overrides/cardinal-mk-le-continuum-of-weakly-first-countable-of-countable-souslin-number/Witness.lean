/-! Non-vacuity witness (D-4 step 7): the one-point space is T3.5, weakly first countable and has countable Souslin number. (Written unchecked; the statement's own identifiers `WeaklyFirstCountableTopology` and `HasCountableSouslinNumber` are not defined by any ported module.) -/

theorem witness : ∃ (X : Type) (_ : TopologicalSpace X),
    T35Space X ∧ WeaklyFirstCountableTopology X ∧ HasCountableSouslinNumber X :=
  ⟨Unit, inferInstance, inferInstance, inferInstance, inferInstance⟩
