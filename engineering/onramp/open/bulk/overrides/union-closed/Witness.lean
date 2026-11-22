/-! Non-vacuity witness (D-4 step 7): on a one-point type, the family {{()}} is not {∅}; the statement's `IsUnionClosed` is not among the ported definitions and cannot be named here (the family is union-closed, its only union being {()} ∪ {()} = {()}). -/

theorem witness : ∃ (n : Type) (A : Finset (Finset n)) (inst : Nonempty n), A ≠ {∅} :=
  ⟨Unit, {{()}}, inferInstance, by decide⟩
