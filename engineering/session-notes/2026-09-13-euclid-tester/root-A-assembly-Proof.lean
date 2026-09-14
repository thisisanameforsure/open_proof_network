import Defs.IsPrime
import Mathlib.Tactic
import Nodes.«infinitude-of-primes».Context

/-! Euclid's theorem (Elements IX.20), over the graph's own `IsPrime` (F11-T1): for every `n`
there is a prime greater than `n`. The statement carries `Mathlib.Tactic` so a prover may use
Mathlib's tactics beneath the local definitions (F11-R7, Q16); a proof is this file with the
`sorry` replaced, header included. -/

theorem Opn.infinitude_of_primes : ∀ n : Nat, ∃ p : Nat, n < p ∧ Opn.IsPrime p := by
  intro n
  -- The merged skeleton's assembly, with each `sorry` replaced by its hole node (declared deps).
  have dvd_fact := infinitude_of_primes__h1 n
  have prime_divisor := infinitude_of_primes__h2 n dvd_fact
  have dvd_consecutive := infinitude_of_primes__h3 n dvd_fact prime_divisor
  have fact_pos := infinitude_of_primes__h4 n dvd_fact prime_divisor dvd_consecutive
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
