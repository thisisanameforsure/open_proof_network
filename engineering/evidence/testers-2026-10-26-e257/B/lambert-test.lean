import Mathlib

private def dd (n : ℕ) : ℕ := n.divisors.card

private def fB (B : Set ℕ) [DecidablePred (· ∈ B)] (n : ℕ) : ℕ :=
  (n.divisors.filter (· ∈ B)).card

private lemma tsum_pnat_of_zero (f : ℕ → ℝ) (h0 : f 0 = 0) : ∑' n : ℕ+, f n = ∑' n : ℕ, f n := by
  apply Function.Injective.tsum_eq PNat.coe_injective
  intro n hn
  have : n ≠ 0 := by rintro rfl; exact hn h0
  exact ⟨⟨n, Nat.pos_of_ne_zero this⟩, rfl⟩

private lemma geom_pnat {x : ℝ} (hx : |x| < 1) : ∑' c : ℕ+, x ^ (c : ℕ) = x / (1 - x) := by
  rw [tsum_pnat_eq_tsum_succ (f := fun m : ℕ => x ^ m)]
  simp_rw [pow_succ]
  rw [tsum_mul_right, tsum_geometric_of_abs_lt_one hx]
  ring

/- The Lambert identity for a set: `∑_{n ∈ B} 1/(2^n - 1) = ∑_m f_B(m) / 2^m`. -/
private lemma lambert_set (B : Set ℕ) [DecidablePred (· ∈ B)] :
    ∑' (n : (↑B : Type)), (1 : ℝ) / ((2 : ℝ) ^ (↑n : ℕ) - (1 : ℝ))
      = ∑' m : ℕ, (fB B m : ℝ) / 2 ^ m := by
  set w : ℕ → ℝ := fun d => if d ∈ B then 1 else 0 with hw
  have hw01 : ∀ d, 0 ≤ w d ∧ w d ≤ 1 := fun d => by
    simp only [hw]; split_ifs <;> norm_num
  set r : ℝ := 1 / 2 with hr
  have hr1 : ‖r‖ < 1 := by rw [hr, Real.norm_eq_abs, abs_of_pos (by norm_num)]; norm_num
  set G : ℕ+ × ℕ+ → ℝ := fun c => w c.1 * r ^ ((c.1 : ℕ) * (c.2 : ℕ)) with hG
  have hGs : Summable G := by
    have h := summable_prod_mul_pow (𝕜 := ℝ) 0 hr1
    refine Summable.of_nonneg_of_le (fun c => ?_) (fun c => ?_) h
    · exact mul_nonneg (hw01 _).1 (by positivity)
    · simp only [pow_zero, one_mul]
      exact mul_le_of_le_one_left (by positivity) (hw01 _).2
  have hprod : ∑' c : ℕ+ × ℕ+, G c = ∑' d : ℕ+, w d / (2 ^ (d : ℕ) - 1) := by
    rw [hGs.tsum_prod]
    refine tsum_congr fun d => ?_
    simp only [hG]
    simp_rw [pow_mul]
    rw [tsum_mul_left, geom_pnat ?_]
    · have h3 : (2:ℝ) ^ (d:ℕ) - 1 ≠ 0 := by
        have : (1:ℝ) < 2 ^ (d:ℕ) := one_lt_pow₀ (by norm_num) d.ne_zero
        linarith
      rw [hr, one_div_pow]
      field_simp
    · rw [hr, one_div_pow, abs_of_pos (by positivity), div_lt_one (by positivity)]
      exact one_lt_pow₀ (by norm_num) d.ne_zero
  have hsig : ∑' c : ℕ+ × ℕ+, G c = ∑' e : ℕ+, (fB B e : ℝ) * r ^ (e : ℕ) := by
    rw [← sigmaAntidiagonalEquivProd.tsum_eq]
    have hs : Summable (fun x => G (sigmaAntidiagonalEquivProd x)) :=
      (Equiv.summable_iff _).2 hGs
    rw [hs.tsum_sigma]
    refine tsum_congr fun e => ?_
    rw [tsum_fintype]
    simp only [sigmaAntidiagonalEquivProd, divisorsAntidiagonalFactors, Equiv.coe_fn_mk,
      PNat.mk_coe, hG]
    rw [Finset.univ_eq_attach,
      (e : ℕ).divisorsAntidiagonal.sum_attach (fun x : ℕ × ℕ => w x.1 * r ^ (x.1 * x.2)),
      Nat.sum_divisorsAntidiagonal (fun a b => w a * r ^ (a * b))]
    rw [Finset.sum_congr rfl (fun a ha => by
      rw [Nat.mul_div_cancel' (Nat.dvd_of_mem_divisors ha)] :
        ∀ a ∈ (e : ℕ).divisors, w a * r ^ (a * ((e : ℕ) / a)) = w a * r ^ (e : ℕ))]
    rw [← Finset.sum_mul]
    congr 1
    unfold fB
    rw [Finset.card_filter]
    push_cast
    rfl
  have hL : ∑' (n : (↑B : Type)), (1 : ℝ) / ((2 : ℝ) ^ (↑n : ℕ) - (1 : ℝ))
      = ∑' d : ℕ+, w d / (2 ^ (d : ℕ) - 1) := by
    rw [tsum_subtype B (fun n : ℕ => (1 : ℝ) / ((2:ℝ) ^ n - 1))]
    rw [tsum_pnat_of_zero (fun n : ℕ => w n / (2 ^ n - 1)) (by simp)]
    refine tsum_congr fun n => ?_
    simp only [Set.indicator_apply, hw]
    split_ifs <;> simp
  have hR : ∑' m : ℕ, (fB B m : ℝ) / 2 ^ m = ∑' e : ℕ+, (fB B e : ℝ) * r ^ (e : ℕ) := by
    rw [← tsum_pnat_of_zero (fun m : ℕ => (fB B m : ℝ) / 2 ^ m) (by simp [fB])]
    refine tsum_congr fun e => ?_
    rw [hr, one_div_pow, div_eq_mul_inv, one_div]
  rw [hL, hR, ← hprod, ← hsig]

theorem foo : True := trivial
