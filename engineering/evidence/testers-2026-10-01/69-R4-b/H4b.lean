import Mathlib
import Defs.Construction

/-- h4a (exact cancellation), general even `M`: at every depth `1 ≤ u ≤ 3M` the signed number of
lines through any point is zero. Proof: depth `u` belongs to exactly one triple `r < M`; a
sign-reversing involution of the six lines of that triple preserves the point at depth `u`. -/
theorem erdos_69__h4__h1 : ∀ (M P u x : ℕ), Even M → 1 ≤ u → u ≤ 3 * M →
    ∑ d ∈ Finset.univ.filter (fun d : Fin M → Fin 6 =>
      Opn.E69.shift M P d + Opn.E69.dil M P d * u = x), Opn.E69.sign M d = 0 := by
  intro M P u x hM hu1 hu2
  -- the tables: at each depth of triple `r` the six lines pair off with opposite signs
  have pair : ∀ r u : ℕ,
      ((r % 2 = 0 ∧ (u = 3 * r + 1 ∨ u = 3 * r + 2 ∨ u = 3 * r + 4)) ∨
        (r % 2 = 1 ∧ (u = 3 * r ∨ u = 3 * r + 2 ∨ u = 3 * r + 3))) →
      ∃ π : Fin 6 → Fin 6, (∀ k, π (π k) = k) ∧
        (∀ k, (-1 : ℤ) ^ ((π k : Fin 6) : ℕ) = -(-1) ^ ((k : Fin 6) : ℕ)) ∧
        ∀ k, Opn.E69.sDigit r (π k) + Opn.E69.gDigit r (π k) * u
          = Opn.E69.sDigit r k + Opn.E69.gDigit r k * u := by
    intro r u h
    rcases h with ⟨hr, h | h | h⟩ | ⟨hr, h | h | h⟩
    · refine ⟨![1, 0, 5, 4, 3, 2], by decide, by decide, fun k => ?_⟩
      subst h; unfold Opn.E69.sDigit Opn.E69.gDigit
      fin_cases k <;> simp [hr] <;> omega
    · refine ⟨![5, 4, 3, 2, 1, 0], by decide, by decide, fun k => ?_⟩
      subst h; unfold Opn.E69.sDigit Opn.E69.gDigit
      fin_cases k <;> simp [hr] <;> omega
    · refine ⟨![3, 2, 1, 0, 5, 4], by decide, by decide, fun k => ?_⟩
      subst h; unfold Opn.E69.sDigit Opn.E69.gDigit
      fin_cases k <;> simp [hr] <;> omega
    · have hr' : ¬ r % 2 = 0 := by omega
      refine ⟨![1, 0, 5, 4, 3, 2], by decide, by decide, fun k => ?_⟩
      subst h; unfold Opn.E69.sDigit Opn.E69.gDigit
      fin_cases k <;> simp [hr] <;> omega
    · have hr' : ¬ r % 2 = 0 := by omega
      refine ⟨![5, 4, 3, 2, 1, 0], by decide, by decide, fun k => ?_⟩
      subst h; unfold Opn.E69.sDigit Opn.E69.gDigit
      fin_cases k <;> simp [hr] <;> omega
    · have hr' : ¬ r % 2 = 0 := by omega
      refine ⟨![3, 2, 1, 0, 5, 4], by decide, by decide, fun k => ?_⟩
      subst h; unfold Opn.E69.sDigit Opn.E69.gDigit
      fin_cases k <;> simp [hr] <;> omega
  -- every depth `1 ≤ u ≤ 3M` (M even) lies in a triple `r < M`
  have cover : ∃ r : ℕ, r < M ∧
      ((r % 2 = 0 ∧ (u = 3 * r + 1 ∨ u = 3 * r + 2 ∨ u = 3 * r + 4)) ∨
        (r % 2 = 1 ∧ (u = 3 * r ∨ u = 3 * r + 2 ∨ u = 3 * r + 3))) := by
    obtain ⟨N, rfl⟩ := hM
    have hb : (u - 1) % 6 < 6 := Nat.mod_lt _ (by norm_num)
    by_cases h0 : (u - 1) % 6 = 0 ∨ (u - 1) % 6 = 1 ∨ (u - 1) % 6 = 3
    · exact ⟨2 * ((u - 1) / 6), by omega, by omega⟩
    · exact ⟨2 * ((u - 1) / 6) + 1, by omega, by omega⟩
  obtain ⟨r, hrM, hr⟩ := cover
  obtain ⟨π, hπ, hsgn, hpt⟩ := pair r u hr
  set r0 : Fin M := ⟨r, hrM⟩ with hr0
  set φ : (Fin M → Fin 6) → (Fin M → Fin 6) := fun d => Function.update d r0 (π (d r0)) with hφ
  have hinv : Function.Involutive φ := by
    intro d
    funext i
    by_cases hi : i = r0
    · subst hi; simp [hφ, hπ]
    · simp [hφ, Function.update_of_ne hi]
  have hφr : ∀ d, φ d r0 = π (d r0) := fun d => by simp [hφ]
  have hφne : ∀ d, ∀ i ∈ (Finset.univ : Finset (Fin M)).erase r0, φ d i = d i := by
    intro d i hi
    have : i ≠ r0 := (Finset.mem_erase.mp hi).1
    simp [hφ, Function.update_of_ne this]
  have hmem : r0 ∈ (Finset.univ : Finset (Fin M)) := Finset.mem_univ _
  have hsign : ∀ d, Opn.E69.sign M (φ d) = -Opn.E69.sign M d := by
    intro d
    unfold Opn.E69.sign
    rw [← Finset.mul_prod_erase _ _ hmem, ← Finset.mul_prod_erase _ (fun i => (-1 : ℤ) ^ ((d i : Fin 6) : ℕ)) hmem,
      hφr, hsgn, Finset.prod_congr rfl (fun i hi => by rw [hφne d i hi])]
    ring
  have hkey : ∀ d, Opn.E69.sIndex M (φ d) + Opn.E69.gIndex M (φ d) * u
      = Opn.E69.sIndex M d + Opn.E69.gIndex M d * u := by
    intro d
    have hs : ∀ e : Fin M → Fin 6, Opn.E69.sIndex M e = 7 ^ r * Opn.E69.sDigit r (e r0)
        + ∑ i ∈ (Finset.univ : Finset (Fin M)).erase r0, 7 ^ (i : ℕ) * Opn.E69.sDigit i (e i) :=
      fun e => (Finset.add_sum_erase _ (fun i : Fin M => 7 ^ (i : ℕ) * Opn.E69.sDigit i (e i)) hmem).symm
    have hg : ∀ e : Fin M → Fin 6, Opn.E69.gIndex M e = 7 ^ r * Opn.E69.gDigit r (e r0)
        + ∑ i ∈ (Finset.univ : Finset (Fin M)).erase r0, 7 ^ (i : ℕ) * Opn.E69.gDigit i (e i) :=
      fun e => (Finset.add_sum_erase _ (fun i : Fin M => 7 ^ (i : ℕ) * Opn.E69.gDigit i (e i)) hmem).symm
    have hRs : ∑ i ∈ (Finset.univ : Finset (Fin M)).erase r0, 7 ^ (i : ℕ) * Opn.E69.sDigit i (φ d i)
        = ∑ i ∈ (Finset.univ : Finset (Fin M)).erase r0, 7 ^ (i : ℕ) * Opn.E69.sDigit i (d i) :=
      Finset.sum_congr rfl (fun i hi => by rw [hφne d i hi])
    have hRg : ∑ i ∈ (Finset.univ : Finset (Fin M)).erase r0, 7 ^ (i : ℕ) * Opn.E69.gDigit i (φ d i)
        = ∑ i ∈ (Finset.univ : Finset (Fin M)).erase r0, 7 ^ (i : ℕ) * Opn.E69.gDigit i (d i) :=
      Finset.sum_congr rfl (fun i hi => by rw [hφne d i hi])
    have e : ∀ a b R R' : ℕ, 7 ^ r * a + R + (7 ^ r * b + R') * u
        = 7 ^ r * (a + b * u) + (R + R' * u) := by intros; ring
    rw [hs (φ d), hs d, hg (φ d), hg d, hRs, hRg, hφr, e, e, hpt]
  have hpred : ∀ d, (Opn.E69.shift M P (φ d) + Opn.E69.dil M P (φ d) * u = x)
      ↔ (Opn.E69.shift M P d + Opn.E69.dil M P d * u = x) := by
    intro d
    have e : ∀ s g : ℕ, primorial P * s + (1 + primorial P * (1 + g)) * u
        = primorial P * (s + g * u) + (u + primorial P * u) := by intros; ring
    unfold Opn.E69.shift Opn.E69.dil
    rw [e, e, hkey d]
  rw [Finset.sum_filter]
  have hS : ∑ d : Fin M → Fin 6, (if Opn.E69.shift M P d + Opn.E69.dil M P d * u = x
        then Opn.E69.sign M d else 0)
      = ∑ d : Fin M → Fin 6, (if Opn.E69.shift M P (φ d) + Opn.E69.dil M P (φ d) * u = x
        then Opn.E69.sign M (φ d) else 0) :=
    (Equiv.sum_comp (hinv.toPerm φ) (fun d => if Opn.E69.shift M P d + Opn.E69.dil M P d * u = x
        then Opn.E69.sign M d else 0)).symm
  have hN : ∑ d : Fin M → Fin 6, (if Opn.E69.shift M P (φ d) + Opn.E69.dil M P (φ d) * u = x
        then Opn.E69.sign M (φ d) else 0)
      = -∑ d : Fin M → Fin 6, (if Opn.E69.shift M P d + Opn.E69.dil M P d * u = x
        then Opn.E69.sign M d else 0) := by
    rw [← Finset.sum_neg_distrib]
    refine Finset.sum_congr rfl fun d _ => ?_
    simp only [hpred d, hsign d]
    split_ifs <;> simp
  linarith

open scoped ArithmeticFunction.omega

/-- h4b (what is left), general even `M`: on an admissible base the signed combination is
`2^(-3M)` times the signed combination of the tails started `3M` steps later; the same for the
combination cut at any `z`. From h4a: the first `3M` terms of the tails cancel exactly. -/
theorem erdos_69__h4__h2 : ∀ (M P n₀ t : ℕ), Even M → Opn.E69.Admissible M P n₀ →
    (Opn.E69.signedTail M P n₀ t = (1 / 2 ^ (3 * M) : ℝ) *
      ∑ d : Fin M → Fin 6, (Opn.E69.sign M d : ℝ) * Opn.E69.tail (Opn.E69.dil M P d)
        (Opn.E69.start M P n₀ d + Opn.E69.step M P d * t + 3 * M)) ∧
    ∀ z : ℕ, Opn.E69.signedTailBelow z M P n₀ t = (1 / 2 ^ (3 * M) : ℝ) *
      ∑ d : Fin M → Fin 6, (Opn.E69.sign M d : ℝ) * Opn.E69.tailBelow z (Opn.E69.dil M P d)
        (Opn.E69.start M P n₀ d + Opn.E69.step M P d * t + 3 * M) := by
  intro M P n₀ t hM hadm
  have gen : ∀ F : ℕ → ℕ, (∀ y, F y ≤ y + 1) →
      ∑ d : Fin M → Fin 6, (Opn.E69.sign M d : ℝ) *
        ∑' k : ℕ, (F (Opn.E69.dil M P d *
          (Opn.E69.start M P n₀ d + Opn.E69.step M P d * t + (k + 1))) : ℝ) / 2 ^ (k + 1)
      = (1 / 2 ^ (3 * M) : ℝ) * ∑ d : Fin M → Fin 6, (Opn.E69.sign M d : ℝ) *
        ∑' k : ℕ, (F (Opn.E69.dil M P d *
          (Opn.E69.start M P n₀ d + Opn.E69.step M P d * t + 3 * M + (k + 1))) : ℝ) / 2 ^ (k + 1) := by
    intro F hF
    have hr : ‖(1 / 2 : ℝ)‖ < 1 := by norm_num
    have hS : Summable (fun k : ℕ => ((k : ℝ) + 1) * (1 / 2 : ℝ) ^ (k + 1)) := by
      have h0 := (hasSum_coe_mul_geometric_of_norm_lt_one hr).summable
      have h1 := (summable_nat_add_iff 1).2 h0
      simpa [Nat.cast_add, Nat.cast_one] using h1
    have hsumm : ∀ a m : ℕ, Summable (fun k : ℕ => (F (a * (m + (k + 1))) : ℝ) / 2 ^ (k + 1)) := by
      intro a m
      refine Summable.of_nonneg_of_le (fun k => by positivity) (fun k => ?_)
        (hS.mul_left ((((a * (m + 1) : ℕ) : ℝ)) + 1))
      have h : m + (k + 1) ≤ (m + 1) * (k + 1) := by nlinarith
      have h1 : F (a * (m + (k + 1))) ≤ (a * (m + 1) + 1) * (k + 1) := by
        have e : (a * (m + 1) + 1) * (k + 1) = a * ((m + 1) * (k + 1)) + (k + 1) := by ring
        have h3 := hF (a * (m + (k + 1)))
        have h4 : a * (m + (k + 1)) ≤ a * ((m + 1) * (k + 1)) := Nat.mul_le_mul_left a h
        omega
      have h2 : (F (a * (m + (k + 1))) : ℝ) ≤ (((a * (m + 1) : ℕ) : ℝ) + 1) * ((k : ℝ) + 1) := by
        exact_mod_cast h1
      have hp : (0 : ℝ) < 2 ^ (k + 1) := by positivity
      rw [div_le_iff₀ hp, one_div_pow, mul_assoc, mul_assoc, one_div_mul_cancel hp.ne', mul_one]
      exact h2
    have hsplit : ∀ a m : ℕ, ∑' k : ℕ, (F (a * (m + (k + 1))) : ℝ) / 2 ^ (k + 1)
        = ∑ k ∈ Finset.range (3 * M), (F (a * (m + (k + 1))) : ℝ) / 2 ^ (k + 1)
          + (1 / 2 ^ (3 * M) : ℝ) * ∑' k : ℕ, (F (a * (m + 3 * M + (k + 1))) : ℝ) / 2 ^ (k + 1) := by
      intro a m
      have h := (hsumm a m).sum_add_tsum_nat_add (3 * M)
      rw [← h, ← tsum_mul_left]
      congr 1
      refine tsum_congr fun k => ?_
      rw [show m + (k + 3 * M + 1) = m + 3 * M + (k + 1) by ring,
        show k + 3 * M + 1 = 3 * M + (k + 1) by ring, pow_add]
      field_simp
    have harg : ∀ (d : Fin M → Fin 6) (k : ℕ), Opn.E69.dil M P d *
        (Opn.E69.start M P n₀ d + Opn.E69.step M P d * t + (k + 1))
        = n₀ + Opn.E69.modulus M P * t + (Opn.E69.shift M P d + Opn.E69.dil M P d * (k + 1)) := by
      intro d k
      have h1 : Opn.E69.dil M P d * Opn.E69.start M P n₀ d = n₀ + Opn.E69.shift M P d := by
        unfold Opn.E69.start
        exact Nat.mul_div_cancel' (hadm d)
      have h2 : Opn.E69.dil M P d * Opn.E69.step M P d = Opn.E69.modulus M P := by
        unfold Opn.E69.step Opn.E69.modulus
        exact Nat.mul_div_cancel'
          (Finset.dvd_prod_of_mem (fun d => Opn.E69.dil M P d) (Finset.mem_univ d))
      calc Opn.E69.dil M P d * (Opn.E69.start M P n₀ d + Opn.E69.step M P d * t + (k + 1))
          = Opn.E69.dil M P d * Opn.E69.start M P n₀ d
            + Opn.E69.dil M P d * Opn.E69.step M P d * t + Opn.E69.dil M P d * (k + 1) := by ring
        _ = _ := by rw [h1, h2]; ring
    have hcol : ∀ k ∈ Finset.range (3 * M), ∑ d : Fin M → Fin 6, (Opn.E69.sign M d : ℝ) *
        ((F (Opn.E69.dil M P d *
          (Opn.E69.start M P n₀ d + Opn.E69.step M P d * t + (k + 1))) : ℝ) / 2 ^ (k + 1)) = 0 := by
      intro k hk
      have hk' := Finset.mem_range.mp hk
      have key : ∀ y : ℕ, ∑ d ∈ Finset.univ.filter (fun d : Fin M → Fin 6 =>
          Opn.E69.shift M P d + Opn.E69.dil M P d * (k + 1) = y), (Opn.E69.sign M d : ℝ) *
            ((F (Opn.E69.dil M P d *
              (Opn.E69.start M P n₀ d + Opn.E69.step M P d * t + (k + 1))) : ℝ) / 2 ^ (k + 1)) = 0 := by
        intro y
        have h0 := erdos_69__h4__h1 M P (k + 1) y hM (by omega) (by omega)
        have hc : ∑ d ∈ Finset.univ.filter (fun d : Fin M → Fin 6 =>
            Opn.E69.shift M P d + Opn.E69.dil M P d * (k + 1) = y), (Opn.E69.sign M d : ℝ) = 0 := by
          exact_mod_cast h0
        have : ∑ d ∈ Finset.univ.filter (fun d : Fin M → Fin 6 =>
            Opn.E69.shift M P d + Opn.E69.dil M P d * (k + 1) = y), (Opn.E69.sign M d : ℝ) *
              ((F (Opn.E69.dil M P d *
                (Opn.E69.start M P n₀ d + Opn.E69.step M P d * t + (k + 1))) : ℝ) / 2 ^ (k + 1))
            = (∑ d ∈ Finset.univ.filter (fun d : Fin M → Fin 6 =>
              Opn.E69.shift M P d + Opn.E69.dil M P d * (k + 1) = y), (Opn.E69.sign M d : ℝ)) *
              ((F (n₀ + Opn.E69.modulus M P * t + y) : ℝ) / 2 ^ (k + 1)) := by
          rw [Finset.sum_mul]
          refine Finset.sum_congr rfl fun d hd => ?_
          rw [harg d k, (Finset.mem_filter.mp hd).2]
        rw [this, hc, zero_mul]
      rw [← Finset.sum_fiberwise_of_maps_to
        (g := fun d : Fin M → Fin 6 => Opn.E69.shift M P d + Opn.E69.dil M P d * (k + 1))
        (t := Finset.univ.image
          (fun d : Fin M → Fin 6 => Opn.E69.shift M P d + Opn.E69.dil M P d * (k + 1)))
        (fun d _ => Finset.mem_image_of_mem _ (Finset.mem_univ d))]
      exact Finset.sum_eq_zero fun y _ => key y
    have hzero : ∑ d : Fin M → Fin 6, (Opn.E69.sign M d : ℝ) *
        ∑ k ∈ Finset.range (3 * M), (F (Opn.E69.dil M P d *
          (Opn.E69.start M P n₀ d + Opn.E69.step M P d * t + (k + 1))) : ℝ) / 2 ^ (k + 1) = 0 := by
      simp_rw [Finset.mul_sum]
      rw [Finset.sum_comm]
      exact Finset.sum_eq_zero hcol
    rw [Finset.sum_congr rfl (fun d _ => by rw [hsplit, mul_add]), Finset.sum_add_distrib, hzero,
      zero_add, Finset.mul_sum]
    refine Finset.sum_congr rfl fun d _ => ?_
    ring
  have hω : ∀ y : ℕ, ω y = y.primeFactors.card := fun y => by
    rw [ArithmeticFunction.cardDistinctFactors_apply, Nat.primeFactors, List.card_toFinset]
  have hcard : ∀ y : ℕ, y.primeFactors.card ≤ y + 1 := by
    intro y
    have hsub : y.primeFactors ⊆ Finset.range (y + 1) := by
      intro p hp
      have hp' := Nat.mem_primeFactors.1 hp
      exact Finset.mem_range.2 (Nat.lt_succ_of_le (Nat.le_of_dvd (Nat.pos_of_ne_zero hp'.2.2) hp'.2.1))
    have := Finset.card_le_card hsub
    rwa [Finset.card_range] at this
  refine ⟨?_, fun z => ?_⟩
  · unfold Opn.E69.signedTail Opn.E69.tail
    exact gen (fun y => ω y) (fun y => by rw [hω]; exact hcard y)
  · unfold Opn.E69.signedTailBelow Opn.E69.tailBelow
    exact gen (fun y => Opn.E69.omegaBelow z y) (fun y => by
      unfold Opn.E69.omegaBelow
      exact le_trans (Finset.card_le_card (Finset.filter_subset _ _)) (hcard y))
