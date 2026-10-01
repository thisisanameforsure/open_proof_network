/-! F02 hazard fixture (F02-T9): `auto-implicit` and nothing else. `n` is never declared; with
`autoImplicit` on (Lean core's default, and the gate elaborates with the defaults) it becomes
`∀ {n : Nat}, …`, a binder the author did not write and a reader cannot see. -/

theorem OpnHazard.auto_implicit : n + 0 = n := by
  sorry
