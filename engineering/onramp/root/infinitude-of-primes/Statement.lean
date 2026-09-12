import Defs.IsPrime
import Mathlib.Tactic
import Nodes.«infinitude-of-primes».Context

/-! Euclid's theorem (Elements IX.20), over the graph's own `IsPrime` (F11-T1): for every `n`
there is a prime greater than `n`. The statement carries `Mathlib.Tactic` so a prover may use
Mathlib's tactics beneath the local definitions (F11-R7, Q16); a proof is this file with the
`sorry` replaced, header included. -/

theorem Opn.infinitude_of_primes : ∀ n : Nat, ∃ p : Nat, n < p ∧ Opn.IsPrime p := by
  sorry
