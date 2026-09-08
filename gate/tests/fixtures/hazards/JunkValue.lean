/-! F02 hazard fixture: `junk-value` and nothing else — `head!` on a possibly empty list. The
same subterm appears twice and must yield one finding (F02-Q4). -/

theorem OpnHazard.junk_value : ∀ l : List Nat, l.head! ≤ l.length + l.head! := by
  sorry
