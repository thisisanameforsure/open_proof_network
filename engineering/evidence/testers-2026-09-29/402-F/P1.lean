import Mathlib

/-! The structure lemma every fixed-size case of Erdős problem 402 (Graham's gcd problem) repeats:
with M the largest element of A, if gcd(M, x) > M/n for every x in A, then every other element
of A is (j/k)·M with 1 ≤ j < k < n. A card-n variant needs it with n = A.card: when some x has
gcd(M, x) ≤ M/n the pair (M, x) already answers, and otherwise every element is one of finitely
many fractions of M, which a finite check finishes. -/

theorem Opn.erdos_402_max_fraction_form :
    ∀ (n : ℕ) (A : Finset ℕ) (hne : A.Nonempty), 0 ∉ A →
      (∀ x ∈ A, A.max' hne < (A.max' hne).gcd x * n) →
      ∀ x ∈ A.erase (A.max' hne), ∃ j k : ℕ, 1 ≤ j ∧ j < k ∧ k < n ∧ k * x = j * A.max' hne := by
  intro n A hne hA hw x hx
  rw [Finset.mem_erase] at hx
  obtain ⟨hxM, hxA⟩ := hx
  have hxpos : 0 < x := Nat.pos_of_ne_zero (fun h => hA (h ▸ hxA))
  have hlt : x < A.max' hne := lt_of_le_of_ne (Finset.le_max' A x hxA) hxM
  have hg := hw x hxA
  have hgpos : 0 < (A.max' hne).gcd x := Nat.gcd_pos_of_pos_right _ hxpos
  obtain ⟨k, hk⟩ := Nat.gcd_dvd_left (A.max' hne) x
  obtain ⟨j, hj⟩ := Nat.gcd_dvd_right (A.max' hne) x
  refine ⟨j, k, ?_, ?_, ?_, ?_⟩
  · rcases Nat.eq_zero_or_pos j with h | h
    · rw [h, Nat.mul_zero] at hj
      omega
    · exact h
  · have h1 : (A.max' hne).gcd x * j < (A.max' hne).gcd x * k := by
      rw [← hj, ← hk]
      exact hlt
    exact Nat.lt_of_mul_lt_mul_left h1
  · have h1 : (A.max' hne).gcd x * k < (A.max' hne).gcd x * n := by
      rw [← hk]
      exact hg
    exact Nat.lt_of_mul_lt_mul_left h1
  · calc k * x = k * ((A.max' hne).gcd x * j) := by rw [← hj]
      _ = j * ((A.max' hne).gcd x * k) := by ring
      _ = j * A.max' hne := by rw [← hk]
