import Defs.IsPrime
import Nodes.«infinitude-of-primes».Context

/-! Euclid's theorem (Elements IX.20), over the graph's own `IsPrime`: the on-ramp root. -/

theorem Opn.infinitude_of_primes : ∀ n : Nat, ∃ p : Nat, n < p ∧ Opn.IsPrime p := by
  -- annex: e23b7898f6b6145660fbfb022f8fafca801a5faf373b9e08004ea28dc633a973
  intro n
  have dvd_fact : ∀ k : Nat, 0 < k → k ≤ n → Opn.Divides k (Opn.fact n) := sorry
  have prime_divisor : ∀ m : Nat, 2 ≤ m → ∃ p : Nat, Opn.IsPrime p ∧ Opn.Divides p m := sorry
  have dvd_consecutive : ∀ d m : Nat, Opn.Divides d m → Opn.Divides d (m + 1) → d = 1 := sorry
  have two_le : 2 ≤ Opn.fact n + 1 := by
    have := Opn.fact_pos n
    omega
  obtain ⟨p, hp, hdiv⟩ := prime_divisor (Opn.fact n + 1) two_le
  refine ⟨p, ?_, hp⟩
  rcases Nat.lt_or_ge n p with h | h
  · exact h
  · exfalso
    have hpos : 0 < p := by have := hp.1; omega
    have h1 : Opn.Divides p (Opn.fact n) := dvd_fact p hpos h
    have h2 : p = 1 := dvd_consecutive p (Opn.fact n) h1 hdiv
    have := hp.1
    omega
