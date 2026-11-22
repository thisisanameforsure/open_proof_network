/-! Non-vacuity witness (D-4 step 7): n k = (k+1)², strictly increasing, with n k / (k+1) = k + 1 → ∞, so the limsup is ⊤. -/

theorem witness : ∃ (n : ℕ → ℕ), StrictMono n ∧ atTop.limsup (fun k => (n k / k.succ : EReal)) = ⊤ :=
  ⟨fun k => (k + 1) ^ 2, fun a b h => by dsimp only; gcongr, by
    apply Filter.Tendsto.limsup_eq
    have hfun : (fun k : ℕ => (((k + 1) ^ 2 : ℕ) / (k.succ : ℕ) : EReal)) =
        fun k : ℕ => (((k + 1 : ℕ) : ℝ) : EReal) := by
      funext k
      have hk : ((k.succ : ℕ) : EReal) ≠ 0 := by exact_mod_cast Nat.succ_ne_zero k
      rw [Nat.succ_eq_add_one, pow_two, Nat.cast_mul, EReal.mul_div_cancel_right? hk] -- hole: the EReal cancellation lemma name is a guess
      rfl
    rw [hfun]
    exact EReal.tendsto_coe_atTop.comp? (tendsto_natCast_atTop_atTop.comp (tendsto_add_atTop_nat 1))⟩
