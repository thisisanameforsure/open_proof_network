/-! Non-vacuity witness (D-4 step 7): the primes in increasing order, `a i = nth Prime i`, start above 1, increase strictly, and by unique factorisation two distinct exponent vectors give distinct natural numbers, so their Beurling integers differ by at least 1. -/

theorem witness : ∃ (a : ℕ → ℝ), (1 : ℝ) < a (0 : ℕ) ∧ StrictMono a ∧ Erdos951.Erdos951Prop a :=
  ⟨fun i => ((Nat.nth Nat.Prime i : ℕ) : ℝ),
    by simp [Nat.nth_prime_zero_eq_two],
    fun i j h => by
      exact_mod_cast Nat.nth_strictMono Nat.infinite_setOf_prime h,
    fun k ℓ hkl => by
      have hcast : ∀ f : ℕ →₀ ℕ, Erdos951.beurlingInteger (fun i => ((Nat.nth Nat.Prime i : ℕ) : ℝ)) f
          = (((f.mapDomain (Nat.nth Nat.Prime)).prod (· ^ ·) : ℕ) : ℝ) := by
        intro f
        rw [Erdos951.beurlingInteger_def, Finsupp.prod_mapDomain_index_inj (Nat.nth_injective Nat.infinite_setOf_prime)]
        push_cast
        rfl
      have hinj : (k.mapDomain (Nat.nth Nat.Prime)).prod (· ^ ·) ≠ (ℓ.mapDomain (Nat.nth Nat.Prime)).prod (· ^ ·) := by
        intro h
        have hk := Nat.prod_pow_factorization_eq_self (f := k.mapDomain (Nat.nth Nat.Prime))
          (fun p hp => by
            obtain ⟨i, _, rfl⟩ := Finsupp.mapDomain_support_of_injective (Nat.nth_injective Nat.infinite_setOf_prime) k hp
            exact Nat.prime_nth_prime i)
        have hl := Nat.prod_pow_factorization_eq_self (f := ℓ.mapDomain (Nat.nth Nat.Prime))
          (fun p hp => by
            obtain ⟨i, _, rfl⟩ := Finsupp.mapDomain_support_of_injective (Nat.nth_injective Nat.infinite_setOf_prime) ℓ hp
            exact Nat.prime_nth_prime i)
        apply hkl
        apply Finsupp.mapDomain_injective (Nat.nth_injective Nat.infinite_setOf_prime)
        rw [← hk, ← hl, h]
      rw [hcast, hcast, ge_iff_le]
      have hz : (((k.mapDomain (Nat.nth Nat.Prime)).prod (· ^ ·) : ℤ) - ((ℓ.mapDomain (Nat.nth Nat.Prime)).prod (· ^ ·) : ℤ)) ≠ 0 :=
        sub_ne_zero.mpr (by exact_mod_cast hinj)
      have h1 := Int.one_le_abs hz
      exact_mod_cast h1⟩
