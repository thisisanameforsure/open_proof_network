import Defs.IsPrime
import Nodes.«infinitude-of-primes».Context

/-! Euclid's theorem (Elements IX.20), over the graph's own `IsPrime`: the on-ramp root. -/

theorem Opn.infinitude_of_primes : ∀ n : Nat, ∃ p : Nat, n < p ∧ Opn.IsPrime p := by
  -- annex: e23b7898f6b6145660fbfb022f8fafca801a5faf373b9e08004ea28dc633a973
  -- approach: Euclid's argument: a prime divisor of n! + 1 exceeds n
  -- licence: CC-BY-4.0
  intro n
  -- label: every k ≤ n divides n!
  -- claim: $\forall k,\ 0 < k \le n \Rightarrow k \mid n!$
  have dvd_fact : ∀ k : Nat, 0 < k → k ≤ n → Opn.Divides k (Opn.fact n) := sorry
  -- label: every m ≥ 2 has a prime divisor
  -- claim: $\forall m \ge 2,\ \exists p \text{ prime},\ p \mid m$
  have prime_divisor : ∀ m : Nat, 2 ≤ m → ∃ p : Nat, Opn.IsPrime p ∧ Opn.Divides p m := sorry
  -- label: only 1 divides two consecutive numbers
  -- claim: $d \mid m \wedge d \mid m+1 \Rightarrow d = 1$
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
