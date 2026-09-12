import Defs.IsPrime
import Mathlib.Tactic
import Nodes.«infinitude-of-primes».Context

/-! Euclid's theorem (Elements IX.20), over the graph's own `IsPrime` (F11-T1): for every `n`
there is a prime greater than `n`. The statement carries `Mathlib.Tactic` so a prover may use
Mathlib's tactics beneath the local definitions (F11-R7, Q16); a proof is this file with the
`sorry` replaced, header included. -/

theorem Opn.infinitude_of_primes : ∀ n : Nat, ∃ p : Nat, n < p ∧ Opn.IsPrime p := by
  -- annex: e23b7898f6b6145660fbfb022f8fafca801a5faf373b9e08004ea28dc633a973
  -- The factorial is Mathlib's `Nat.factorial`, reached through the statement's own
  -- `Mathlib.Tactic` import: the target's `Opn.fact` (Defs.Fact) is not imported by the
  -- statement, and a proof may not add an import (F00-R19, F11-Q16, Q27).
  intro n
  have dvd_fact : ∀ k : Nat, 0 < k → k ≤ n → Opn.Divides k (Nat.factorial n) := sorry
  have prime_divisor : ∀ m : Nat, 2 ≤ m → ∃ p : Nat, Opn.IsPrime p ∧ Opn.Divides p m := sorry
  have dvd_consecutive : ∀ d m : Nat, Opn.Divides d m → Opn.Divides d (m + 1) → d = 1 := sorry
  have fact_pos : ∀ k : Nat, 0 < Nat.factorial k := sorry
  have two_le : 2 ≤ Nat.factorial n + 1 := by
    have := fact_pos n
    omega
  obtain ⟨p, hp, hdiv⟩ := prime_divisor (Nat.factorial n + 1) two_le
  refine ⟨p, ?_, hp⟩
  rcases Nat.lt_or_ge n p with h | h
  · exact h
  · exfalso
    have hpos : 0 < p := by have := hp.1; omega
    have h1 : Opn.Divides p (Nat.factorial n) := dvd_fact p hpos h
    have h2 : p = 1 := dvd_consecutive p (Nat.factorial n) h1 hdiv
    have := hp.1
    omega
