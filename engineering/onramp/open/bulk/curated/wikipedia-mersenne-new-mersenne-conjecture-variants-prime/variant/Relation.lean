import Mathlib
import Defs.Local

open Mersenne

/-- `resolves`: this variant (odd primes) implies the root (all odd `p`). The proof is the
registry's own `new_mersenne_conjecture_of_prime` (FormalConjectures/Wikipedia/Mersenne.lean at
d8d031d4998c78575159ccab9a7a9e95ce043883, Apache-2.0, The Formal Conjectures Authors), with the
binder order of this variant's statement (`p.Prime → Odd p`). -/
theorem relation :
    (∀ (p : ℕ), p.Prime → Odd p → NewMersenneConjectureStatement p) →
    ∀ (p : ℕ), Odd p → NewMersenneConjectureStatement p := by
  intro H p hp_odd
  by_cases hp_prime : p.Prime
  · exact H p hp_prime hp_odd
  suffices ¬Nat.GivesWagstaffPrime p by
    have hF1 : ¬(mersenne p).Prime := fun h => hp_prime h.of_mersenne
    refine ⟨?_, ?_, ?_⟩ <;> grind
  rintro ⟨_, hP⟩
  by_cases hp1 : p = 1
  · grind
  set q := p.minFac
  have hq_dvd : q ∣ p := Nat.minFac_dvd p
  have hq_ne2 : q ≠ 2 := fun h =>
    Nat.not_even_iff_odd.mpr hp_odd (even_iff_two_dvd.mpr (h ▸ hq_dvd))
  have hq_odd : Odd q := (Nat.minFac_prime hp1).odd_of_ne_two hq_ne2
  obtain ⟨s, hs⟩ := hq_dvd
  have hs_odd : Odd s := (Nat.odd_mul.mp (hs ▸ hp_odd)).2
  have hpow_dvd : 2 ^ q + 1 ∣ 2 ^ p + 1 := by
    grind [one_pow, ← pow_mul, Odd.nat_add_dvd_pow_add_pow (x := 2 ^ q) (y := 1) hs_odd]
  have h3q : 3 ∣ 2 ^ q + 1 := by
    grind [Odd.nat_add_dvd_pow_add_pow (x := 2) (y := 1)]
  have h3p : 3 ∣ 2 ^ p + 1 := h3q.trans hpow_dvd
  obtain ⟨k, hk⟩ := hpow_dvd
  set d := (2 ^ q + 1) / 3 with hd
  have hd_dvd : d ∣ (2 ^ p + 1) / 3 := by
    use k
    grind [mul_comm, Nat.mul_div_assoc, mul_comm]
  have h8 : 8 ≤ 2 ^ q := by
    calc 8 = 2 ^ 3 := by norm_num
      _ ≤ 2 ^ q := Nat.pow_le_pow_right (by norm_num) (by grind [(Nat.minFac_prime hp1).two_le])
  have hd_lt : d < (2 ^ p + 1) / 3 := by
    have hpow : 2 ^ q < 2 ^ p := by
      apply Nat.pow_lt_pow_right <;> grind [Nat.not_prime_iff_minFac_lt]
    grind [Nat.mul_div_cancel_left]
  rcases hP.eq_one_or_self_of_dvd d hd_dvd with h | h <;> grind
