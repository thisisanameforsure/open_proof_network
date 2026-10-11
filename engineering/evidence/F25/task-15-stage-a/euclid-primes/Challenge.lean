module

public import Mathlib.Tactic

-- inlined by the network from Defs.Divides (F13-R5, F25-R8)
/-! Divisibility, written out rather than `Nat.dvd`, so Mathlib's `Dvd` API does not apply to
it by name (F11-T1, R7; D-6): a bridge to `Nat.dvd` is a lemma, not a citation. -/

def Opn.Divides (a b : Nat) : Prop := ∃ c : Nat, b = a * c

-- inlined by the network from Defs.Fact (F13-R5, F25-R8)
/-! The factorial, by recursion; `Nat.factorial`'s lemmas do not apply to it by name. -/

def Opn.fact : Nat → Nat
  | 0 => 1
  | n + 1 => (n + 1) * Opn.fact n

-- inlined by the network from Defs.IsPrime (F13-R5, F25-R8)
/-! A prime, over the graph's own divisibility: at least 2, with only the trivial divisors. -/

def Opn.IsPrime (p : Nat) : Prop := 2 ≤ p ∧ ∀ d : Nat, Opn.Divides d p → d = 1 ∨ d = p

@[expose] public section

/-! Euclid's theorem (Elements IX.20), over the graph's own `IsPrime` (F11-T1): for every `n`
there is a prime greater than `n`. The statement carries `Mathlib.Tactic` so a prover may use
Mathlib's tactics beneath the local definitions (F11-R7, Q16); a proof is this file with the
`sorry` replaced, header included. -/

theorem Opn.infinitude_of_primes : ∀ n : Nat, ∃ p : Nat, n < p ∧ Opn.IsPrime p := by
  sorry
