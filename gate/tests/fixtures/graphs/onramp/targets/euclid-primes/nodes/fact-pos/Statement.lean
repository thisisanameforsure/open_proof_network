import Defs.Fact
import Mathlib.Tactic.Linarith

/-! `fact-pos` (F11-T1's lemma table): the factorial is positive. The statement carries the
Mathlib import a prover may use beneath the local definition (F11-R7): a proof is the statement
with its `sorry` replaced, header included (F00-R19). -/

theorem Opn.fact_pos : ∀ n : Nat, 0 < Opn.fact n := by
  sorry
