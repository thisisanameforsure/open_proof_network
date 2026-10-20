import Mathlib

theorem carry_dvd (n k p : ℕ) (hp : p.Prime) (h : n % p < k % p) : p ∣ n.choose k := by
  haveI := Fact.mk hp
  have hl := Choose.choose_modEq_choose_mod_mul_choose_div_nat (n := n) (k := k) (p := p)
  rw [Nat.choose_eq_zero_of_lt h, zero_mul] at hl
  exact (Nat.modEq_zero_iff_dvd).1 hl

theorem minFac_le_of_carry (n k p : ℕ) (hp : p.Prime) (hpk : p ≤ k) (h : n % p < k % p) :
    (n.choose k).minFac ≤ k :=
  le_trans (Nat.minFac_le_of_dvd hp.two_le (carry_dvd n k p hp h)) hpk
