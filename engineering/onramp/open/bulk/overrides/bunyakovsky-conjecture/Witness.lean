/-! Non-vacuity witness (D-4 step 7): f = X is irreducible of degree 1 with leading coefficient 1, and X(1) = 1 is divisible by no prime. -/

theorem witness : ∃ (f : ℤ[X]), BunyakovskyCondition f ∧ SchinzelCondition {f} :=
  ⟨Polynomial.X,
   ⟨by simp [Polynomial.degree_X], Polynomial.irreducible_X, by simp⟩,
   fun p hp => ⟨1, fun f hf => by
     rw [Finset.mem_singleton] at hf
     subst hf
     rw [Polynomial.eval_X]
     intro h
     have h' : p ∣ 1 := by exact_mod_cast h
     exact hp.ne_one (Nat.dvd_one.mp h')⟩⟩
