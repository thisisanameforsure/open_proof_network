import Mathlib

open scoped Nat

theorem lemB (n k : ℕ) (hk : 0 < k) (hn : k * k ≤ n) (hm : (n.choose k).minFac > n / k) :
    (n / n.gcd k).Prime := by
  have hn0 : 0 < n := lt_of_lt_of_le (Nat.mul_pos hk hk) hn
  have hkn : k ≤ n := le_trans (Nat.le_mul_of_pos_left k hk) hn
  have hkm : k ≤ n / k := (Nat.le_div_iff_mul_le hk).2 hn
  set g := n.gcd k with hg
  have hg0 : 0 < g := Nat.gcd_pos_of_pos_left k hn0
  have hgn : g ∣ n := Nat.gcd_dvd_left n k
  have hgk : g ∣ k := Nat.gcd_dvd_right n k
  -- k * C(n,k) = n * C(n-1,k-1)
  have hid : n * (n - 1).choose (k - 1) = n.choose k * k := by
    have := Nat.add_one_mul_choose_eq (n - 1) (k - 1)
    rwa [Nat.sub_add_cancel (by omega : 1 ≤ n), Nat.sub_add_cancel (by omega : 1 ≤ k)] at this
  have hcop : Nat.Coprime (n / g) (k / g) := Nat.coprime_div_gcd_div_gcd hg0
  have hdvd : n / g ∣ n.choose k := by
    have h1 : n / g ∣ n.choose k * (k / g) := by
      refine ⟨(n - 1).choose (k - 1), ?_⟩
      have e1 : n = n / g * g := (Nat.div_mul_cancel hgn).symm
      have e2 : k = k / g * g := (Nat.div_mul_cancel hgk).symm
      have : n / g * g * (n - 1).choose (k - 1) = n.choose k * (k / g * g) := by
        rw [← e1, ← e2]; exact hid
      have : (n / g * (n - 1).choose (k - 1)) * g = (n.choose k * (k / g)) * g := by
        linear_combination this
      exact (Nat.eq_of_mul_eq_mul_right hg0 this).symm
    exact hcop.dvd_of_dvd_mul_right h1
  have hCpos : 0 < n.choose k := Nat.choose_pos hkn
  -- n/g ≥ n/k ≥ k ≥ 1
  have hng : n / k ≤ n / g := Nat.div_le_div_left (Nat.le_of_dvd hk hgk) hg0
  by_contra hnp
  have h2 : 2 ≤ n / g := by
    rcases Nat.lt_or_ge (n / g) 2 with h | h
    · -- n/g ≤ 1 so n/k ≤ 1 so k = 1, n/k = n
      exfalso
      have hk1 : k ≤ 1 := by omega
      have hk1' : k = 1 := by omega
      subst hk1'
      have : n ≤ 1 := by simpa using (show n / 1 ≤ 1 by omega)
      have hn1 : n = 1 := by omega
      subst hn1
      simp at hm
    · exact h
  -- q := minFac (n/g); q ∣ C so minFac C ≤ q
  have hq2 : 2 ≤ (n / g).minFac := (Nat.minFac_prime (by omega)).two_le
  have hqC : (n.choose k).minFac ≤ (n / g).minFac :=
    Nat.minFac_le_of_dvd hq2 ((Nat.minFac_dvd _).trans hdvd)
  have hsq : (n / g).minFac ^ 2 ≤ n / g := Nat.minFac_sq_le_self (by omega) hnp
  have hq : n / k + 1 ≤ (n / g).minFac := by omega
  have hng' : n / g ≤ n := Nat.div_le_self n g
  have hlt : n < (n / k + 1) * k := by
    have := Nat.lt_mul_div_succ n hk
    linarith [this]
  have : (n / k + 1) * k ≤ (n / k + 1) * (n / k + 1) := Nat.mul_le_mul_left _ (by omega)
  nlinarith
