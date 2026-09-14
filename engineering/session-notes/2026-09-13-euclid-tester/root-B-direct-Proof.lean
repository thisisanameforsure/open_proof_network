import Defs.IsPrime
import Mathlib.Tactic
import Nodes.«infinitude-of-primes».Context

/-! Euclid's theorem (Elements IX.20), over the graph's own `IsPrime` (F11-T1): for every `n`
there is a prime greater than `n`. The statement carries `Mathlib.Tactic` so a prover may use
Mathlib's tactics beneath the local definitions (F11-R7, Q16); a proof is this file with the
`sorry` replaced, header included. -/

theorem Opn.infinitude_of_primes : ∀ n : Nat, ∃ p : Nat, n < p ∧ Opn.IsPrime p := by
  intro n
  -- Self-contained, no dependency nodes: Mathlib's least prime factor of n! + 1, carried to the
  -- graph's `Opn.IsPrime` by a bridge from `Nat.Prime`.
  have bridge : ∀ q : Nat, Nat.Prime q → Opn.IsPrime q := by
    intro q hq
    refine ⟨hq.two_le, ?_⟩
    intro d hd
    have hd' : d ∣ q := hd
    exact (Nat.dvd_prime hq).mp hd'
  have hne : Nat.factorial n + 1 ≠ 1 := by
    have := Nat.factorial_pos n
    omega
  have hprime : Nat.Prime (Nat.minFac (Nat.factorial n + 1)) := Nat.minFac_prime hne
  refine ⟨Nat.minFac (Nat.factorial n + 1), ?_, bridge _ hprime⟩
  rcases Nat.lt_or_ge n (Nat.minFac (Nat.factorial n + 1)) with h | h
  · exact h
  · exfalso
    have hfact : Nat.minFac (Nat.factorial n + 1) ∣ Nat.factorial n :=
      Nat.dvd_factorial (Nat.minFac_pos _) h
    have hone : Nat.minFac (Nat.factorial n + 1) ∣ 1 :=
      (Nat.dvd_add_right hfact).mp (Nat.minFac_dvd _)
    have h2 := hprime.two_le
    have h1 := Nat.le_of_dvd Nat.one_pos hone
    omega
