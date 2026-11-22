/-! Non-vacuity witness (D-4 step 7): the one-element family {X}: X is irreducible of degree 1 with positive leading coefficient, and X(1) = 1 is divisible by no prime. -/

theorem witness : ∃ (polys : Finset ℤ[X]) (h_irreducible : ∀ f ∈ polys, BunyakovskyCondition f)
    (h_compat : SchinzelCondition polys), polys.Nonempty :=
  ⟨{Polynomial.X},
   fun f hf => by
     rw [Finset.mem_singleton] at hf
     subst hf
     exact ⟨by simp [Polynomial.degree_X], Polynomial.irreducible_X, by simp⟩,
   fun p hp => ⟨1, fun f hf => by
     rw [Finset.mem_singleton] at hf
     subst hf
     rw [Polynomial.eval_X]
     intro h
     have h' : p ∣ 1 := by exact_mod_cast h
     exact hp.ne_one (Nat.dvd_one.mp h')⟩,
   Finset.singleton_nonempty _⟩
