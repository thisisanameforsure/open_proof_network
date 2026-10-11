import Mathlib

theorem Opn.erdos_69_rough_dilations_coprime :
    ∀ P i j : ℕ, i ≤ P → j ≤ P → i ≠ j →
      Nat.Coprime (1 + primorial P * (1 + i)) (1 + primorial P * (1 + j)) := by
  intro P i j hi hj hij
  rw [Nat.coprime_iff_gcd_eq_one]
  by_contra hne
  obtain ⟨p, hp, hpd⟩ := Nat.exists_prime_and_dvd hne
  have hdi : p ∣ 1 + primorial P * (1 + i) := hpd.trans (Nat.gcd_dvd_left _ _)
  have hdj : p ∣ 1 + primorial P * (1 + j) := hpd.trans (Nat.gcd_dvd_right _ _)
  -- p exceeds P: otherwise p ∣ P# and so p ∣ 1
  have hbig : P < p := by
    by_contra hle
    push Not at hle
    have hprim : p ∣ primorial P := by
      apply Finset.dvd_prod_of_mem
      rw [Finset.mem_filter, Finset.mem_range]
      exact ⟨by omega, hp⟩
    have h' : p ∣ primorial P * (1 + i) + 1 := by rw [add_comm]; exact hdi
    have h1 : p ∣ 1 := (Nat.dvd_add_right (dvd_mul_of_dvd_left hprim (1 + i))).mp h'
    exact hp.one_lt.ne' (Nat.dvd_one.mp h1)
  -- p divides P# * |i - j|
  have hcop : Nat.Coprime p (primorial P) := by
    rw [Nat.coprime_comm, Nat.Coprime, ← Nat.coprime_iff_gcd_eq_one]
    apply Nat.Coprime.symm
    rw [Nat.Prime.coprime_iff_not_dvd hp]
    intro hdvd
    have h' : p ∣ primorial P * (1 + i) + 1 := by rw [add_comm]; exact hdi
    have h1 : p ∣ 1 := (Nat.dvd_add_right (dvd_mul_of_dvd_left hdvd (1 + i))).mp h'
    exact hp.one_lt.ne' (Nat.dvd_one.mp h1)
  rcases Nat.lt_or_gt_of_ne hij with h | h
  · -- i < j
    have hsub : p ∣ (1 + primorial P * (1 + j)) - (1 + primorial P * (1 + i)) :=
      Nat.dvd_sub hdj hdi
    have heq : (1 + primorial P * (1 + j)) - (1 + primorial P * (1 + i)) = primorial P * (j - i) := by
      have hm := Nat.mul_le_mul_left (primorial P) h.le
      rw [Nat.mul_sub, Nat.mul_add, Nat.mul_add, Nat.mul_one]; omega
    rw [heq] at hsub
    have := (Nat.Coprime.dvd_of_dvd_mul_left hcop hsub)
    have hpos : 0 < j - i := by omega
    have := Nat.le_of_dvd hpos this
    omega
  · have hsub : p ∣ (1 + primorial P * (1 + i)) - (1 + primorial P * (1 + j)) :=
      Nat.dvd_sub hdi hdj
    have heq : (1 + primorial P * (1 + i)) - (1 + primorial P * (1 + j)) = primorial P * (i - j) := by
      have hm := Nat.mul_le_mul_left (primorial P) h.le
      rw [Nat.mul_sub, Nat.mul_add, Nat.mul_add, Nat.mul_one]; omega
    rw [heq] at hsub
    have := (Nat.Coprime.dvd_of_dvd_mul_left hcop hsub)
    have hpos : 0 < i - j := by omega
    have := Nat.le_of_dvd hpos this
    omega
