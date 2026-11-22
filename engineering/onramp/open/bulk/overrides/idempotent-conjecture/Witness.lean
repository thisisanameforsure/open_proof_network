/-! Non-vacuity witness (D-4 step 7): 0 is an idempotent of the monoid algebra ℕ[Unit]. (The statement leaves `K` and `G` auto-bound with no `Semiring`/`Monoid` instances; the witness binds them.) -/

theorem witness : ∃ (K : Type) (G : Type) (_ : Semiring K) (_ : Monoid G) (a : MonoidAlgebra K G),
    IsIdempotentElem a :=
  ⟨ℕ, Unit, inferInstance, inferInstance, 0, IsIdempotentElem.zero⟩
