/-! Non-vacuity witness (D-4 step 7): the entire function ∑ z^(k²)/(k²)!, whose exponents k² have Fabry gaps (k²/k → ∞), whose coefficients are nonzero, and whose series converges everywhere as a subseries of the exponential series. -/

theorem witness : ∃ (f : ℂ → ℂ) (n : ℕ → ℕ) (a : ℕ → ℂ) (z : ℂ),
  HasFabryGaps n ∧ (∀ (k : ℕ), a k ≠ (0 : ℂ)) ∧ ∀ (z : ℂ), HasSum (fun (k : ℕ) => a k * z ^ n k) (f z) := by
  have hinj : Function.Injective (fun k : ℕ => k ^ 2) := fun a b h => by
    exact Nat.pow_left_injective two_ne_zero h
  have hs : ∀ z : ℂ, Summable (fun k : ℕ => (((k ^ 2).factorial : ℂ))⁻¹ * z ^ (k ^ 2)) := by
    intro z
    refine Summable.of_norm ?_
    refine ((Real.summable_pow_div_factorial ‖z‖).comp_injective hinj).congr ?_
    intro k
    simp [Function.comp, norm_mul, norm_inv, norm_pow, div_eq_inv_mul]
  refine ⟨fun z => ∑' k : ℕ, (((k ^ 2).factorial : ℂ))⁻¹ * z ^ (k ^ 2), fun k => k ^ 2,
    fun k => (((k ^ 2).factorial : ℂ))⁻¹, 0, ⟨?_, ?_⟩, ?_, fun z => (hs z).hasSum⟩
  · intro a b h
    exact Nat.pow_lt_pow_left h two_ne_zero
  · refine tendsto_natCast_atTop_atTop.congr' ?_
    filter_upwards [Filter.eventually_gt_atTop 0] with k hk
    have hk' : (k : ℝ) ≠ 0 := by positivity
    push_cast
    rw [eq_div_iff hk']
    ring
  · intro k
    exact inv_ne_zero (Nat.cast_ne_zero.mpr (Nat.factorial_ne_zero _))
