/-! Non-vacuity witness (D-4 step 7): the integers, the group of order two, a one-element index type, the zero matrix (an idempotent) and the generator of order two, whose order 2 is not a unit of ℤ. -/

theorem witness : ∃ (R : Type) (_ : CommRing R) (G : Type) (_ : Group G) (n : Type) (_ : Fintype n)
    (A : Matrix n n (MonoidAlgebra R G)) (g : G),
    IsDomain R ∧ A * A = A ∧ ¬IsUnit ((orderOf g : ℕ) : R) :=
  ⟨ℤ, inferInstance, Multiplicative (ZMod 2), inferInstance, Unit, inferInstance, 0,
    Multiplicative.ofAdd 1, inferInstance, by simp, by
      rw [orderOf_ofAdd_eq_addOrderOf, ZMod.addOrderOf_one]
      norm_num [Int.isUnit_iff]⟩
