/-! Non-vacuity witness (D-4 step 7): the statement's binders are a type with a field structure
of characteristic zero; the rationals, lifted to the statement's universe, are one (characteristic
zero carried across the ring isomorphism `ULift ℚ ≃+* ℚ`). -/

theorem witness : ∃ (K : Type u_1) (inst : Field K), CharZero K :=
  ⟨ULift ℚ, inferInstance, RingHom.charZero (ULift.ringEquiv : ULift ℚ ≃+* ℚ).toRingHom⟩
