import Defs.IsPrime
import Nodes.«infinitude-of-primes».Context

/-! Euclid's theorem (Elements IX.20), over the graph's own `IsPrime`: the on-ramp root. -/

theorem Opn.infinitude_of_primes : ∀ n : Nat, ∃ p : Nat, n < p ∧ Opn.IsPrime p := by
  sorry
