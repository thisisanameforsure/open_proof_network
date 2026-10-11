import Mathlib
import Nodes.«spec-84446025».Context

open scoped ArithmeticFunction.omega

/-! A speculative ingredient for erdos-69 (D-29): the rational side of the composite-dilation route,
packaged. Write `D_a(m) = ∑_{k ≥ 0} ω (a (m + k + 1)) / 2^(k+1)` for the tail dilated by `a`. If
`q · ∑ ω(n)/2^n` is the integer `z`, then along any progression `b + Q t` (`t < T`) with every
prime factor of `a` coprime to `Q`, the numbers `q · D_a(b + Q t)` are on average within
`q · ∑_{p ∣ a} (1/p + 1/T)` of an integer. For a rough dilation `a = 1 + P# (1 + j)` the
node `spec-e0b917d1` bounds `∑_{p ∣ a} 1/p` by `5 / log P`, so rationality forces the dilated tails
close to integers on average; the unconditional half of the route (github.com/plby/lean-proofs,
`ErdosProblems/Erdos69`; see the annex on `erdos-69`) shows a signed combination of them is not.
Proof ingredients: `ω (a n) = ω a + ω n - #{p ∣ a : p ∣ n}`, integrality of `q` times each tail,
and at most `T/p + 1` solutions `t < T` of `p ∣ c + Q t` when `p ∤ Q`. -/

theorem Opn.erdos_69_rational_dilated_tails_near_integers :
    ∀ (q : ℕ) (z : ℤ), (q : ℝ) * ∑' n : ℕ, (ω n : ℝ) / 2 ^ n = z →
      ∀ (a Q b T : ℕ), a ≠ 0 → 0 < T → (∀ p ∈ a.primeFactors, Nat.Coprime p Q) →
        (∑ t ∈ Finset.range T,
            |(q : ℝ) * ∑' k : ℕ, (ω (a * (b + Q * t + (k + 1))) : ℝ) / 2 ^ (k + 1)
              - round ((q : ℝ) * ∑' k : ℕ, (ω (a * (b + Q * t + (k + 1))) : ℝ) / 2 ^ (k + 1))|) / T
          ≤ (q : ℝ) * ∑ p ∈ a.primeFactors, ((1 : ℝ) / p + 1 / T) := by
  have count_le : ∀ (p Q T c : ℕ), Nat.Coprime p Q → 0 < p →
      ((Finset.range T).filter (fun t => p ∣ c + Q * t)).card ≤ T / p + 1 := by
    intro p Q T c hcop hp
    calc ((Finset.range T).filter (fun t => p ∣ c + Q * t)).card
        ≤ (Finset.range (T / p + 1)).card := by
          apply Finset.card_le_card_of_injOn (fun t => t / p)
          · intro t ht
            simp only [Finset.coe_filter, Finset.mem_range, Set.mem_ofPred_eq] at ht
            simp only [Finset.coe_range, Set.mem_Iio]
            have := Nat.div_le_div_right (c := p) (le_of_lt ht.1)
            omega
          · intro t1 ht1 t2 ht2 heq
            simp only [Finset.coe_filter, Finset.mem_range, Set.mem_ofPred_eq] at ht1 ht2
            simp only at heq
            have key : ∀ u v : ℕ, u ≤ v → p ∣ c + Q * u → p ∣ c + Q * v → u / p = v / p → u = v := by
              intro u v huv hu hv hq
              have hd : p ∣ Q * (v - u) := by
                have e : c + Q * v = (c + Q * u) + Q * (v - u) := by
                  rw [Nat.mul_sub, ← Nat.add_sub_assoc (Nat.mul_le_mul_left Q huv)]
                  omega
                rw [e] at hv
                exact (Nat.dvd_add_right hu).mp hv
              have hd' : p ∣ v - u := hcop.dvd_of_dvd_mul_left hd
              have e1 := Nat.div_add_mod u p
              have e2 := Nat.div_add_mod v p
              have m1 := Nat.mod_lt u hp
              have m2 := Nat.mod_lt v hp
              rw [hq] at e1
              have hlt : v - u < p := by
                generalize p * (v / p) = w at *
                omega
              have := Nat.eq_zero_of_dvd_of_lt hd' hlt
              omega
            rcases le_total t1 t2 with h | h
            · exact key t1 t2 h ht1.2 ht2.2 heq
            · exact (key t2 t1 h ht2.2 ht1.2 heq.symm).symm
      _ = T / p + 1 := Finset.card_range _
  have omega_mul_eq : ∀ (a n : ℕ), a ≠ 0 → n ≠ 0 →
      (ω (a * n) : ℝ) = (ω n : ℝ) + (ω a : ℝ)
        - ∑ p ∈ a.primeFactors, (if p ∣ n then (1 : ℝ) else 0) := by
    intro a n ha hn
    have hω : ∀ m : ℕ, ω m = m.primeFactors.card := fun m => by
      rw [ArithmeticFunction.cardDistinctFactors_apply]; rfl
    have hunion : (a * n).primeFactors.card + (a.primeFactors ∩ n.primeFactors).card
        = a.primeFactors.card + n.primeFactors.card := by
      rw [Nat.primeFactors_mul ha hn, Finset.card_union_add_card_inter]
    have hinter : a.primeFactors ∩ n.primeFactors = a.primeFactors.filter (· ∣ n) := by
      ext p
      simp only [Finset.mem_inter, Finset.mem_filter, Nat.mem_primeFactors]
      constructor
      · rintro ⟨h1, h2⟩; exact ⟨h1, h2.2.1⟩
      · rintro ⟨h1, h2⟩; exact ⟨h1, h1.1, h2, hn⟩
    have hsum : (∑ p ∈ a.primeFactors, (if p ∣ n then (1 : ℝ) else 0))
        = ((a.primeFactors.filter (· ∣ n)).card : ℝ) := by
      rw [Finset.card_filter]; push_cast; rfl
    rw [hsum, ← hinter, hω, hω, hω]
    have : ((a * n).primeFactors.card : ℝ) + ((a.primeFactors ∩ n.primeFactors).card : ℝ)
        = (a.primeFactors.card : ℝ) + (n.primeFactors.card : ℝ) := by exact_mod_cast hunion
    linarith
  have dilated_tail : ∀ (a m : ℕ), a ≠ 0 →
      ∑' k : ℕ, (ω (a * (m + (k + 1))) : ℝ) / 2 ^ (k + 1)
        = ∑' k : ℕ, (ω (m + (k + 1)) : ℝ) / 2 ^ (k + 1) + (ω a : ℝ)
          - ∑ p ∈ a.primeFactors,
              ∑' k : ℕ, (if p ∣ m + (k + 1) then (1 : ℝ) else 0) / 2 ^ (k + 1) := by
    intro a m ha
    have hsum0 : Summable (fun n : ℕ => (ω n : ℝ) / 2 ^ n) := by
      have hbound : ∀ n : ℕ,
          (ω n : ℝ) / 2 ^ n ≤ (n : ℝ) ^ 1 * (1 / 2 : ℝ) ^ n + (1 / 2 : ℝ) ^ n := by
        intro n
        have h1 : ω n ≤ n + 1 := by
          rw [ArithmeticFunction.cardDistinctFactors_apply]
          calc n.primeFactorsList.dedup.length = n.primeFactors.card := rfl
            _ ≤ (Finset.range (n + 1)).card :=
                Finset.card_le_card (fun p hp =>
                  Finset.mem_range.2 (Nat.lt_succ_of_le (Nat.le_of_mem_primeFactors hp)))
            _ = n + 1 := Finset.card_range _
        have h2 : (ω n : ℝ) ≤ (n : ℝ) + 1 := by exact_mod_cast h1
        have h4 : (0 : ℝ) ≤ ((2 : ℝ) ^ n)⁻¹ := by positivity
        rw [pow_one, one_div, inv_pow, div_eq_mul_inv]
        nlinarith [mul_le_mul_of_nonneg_right h2 h4]
      refine Summable.of_nonneg_of_le (fun n => by positivity) hbound ?_
      exact (summable_pow_mul_geometric_of_norm_lt_one 1 (by norm_num [Real.norm_eq_abs])).add
        (summable_geometric_of_lt_one (by norm_num) (by norm_num))
    have hsA : Summable (fun k : ℕ => (ω (m + (k + 1)) : ℝ) / 2 ^ (k + 1)) := by
      have h := ((summable_nat_add_iff (m + 1)).mpr hsum0).mul_left ((2 : ℝ) ^ m)
      refine h.congr (fun k => ?_)
      rw [show k + (m + 1) = m + (k + 1) by ring, show m + (k + 1) = (k + 1) + m by ring,
        pow_add]
      field_simp
    have hgeo : Summable (fun k : ℕ => (1 : ℝ) / 2 ^ (k + 1)) := by
      refine (summable_geometric_two.mul_left (1 / 2 : ℝ)).congr (fun k => ?_)
      rw [one_div, one_div, ← inv_pow, pow_succ, mul_comm]
    have h1 : ∑' k : ℕ, (1 : ℝ) / 2 ^ (k + 1) = 1 := by
      calc ∑' k : ℕ, (1 : ℝ) / 2 ^ (k + 1) = ∑' n : ℕ, (1 : ℝ) / 2 / 2 ^ n :=
            tsum_congr (fun k => by ring)
        _ = 1 := tsum_geometric_two' 1
    have hsI : ∀ p ∈ a.primeFactors,
        Summable (fun k : ℕ => (if p ∣ m + (k + 1) then (1 : ℝ) else 0) / 2 ^ (k + 1)) := by
      intro p _
      refine Summable.of_nonneg_of_le (fun k => ?_) (fun k => ?_) hgeo
      · split_ifs <;> positivity
      · split_ifs
        · exact le_rfl
        · rw [zero_div]; positivity
    have hpt : ∀ k : ℕ, (ω (a * (m + (k + 1))) : ℝ) / 2 ^ (k + 1)
        = ((ω (m + (k + 1)) : ℝ) / 2 ^ (k + 1) + (ω a : ℝ) * (1 / 2 ^ (k + 1)))
          - ∑ p ∈ a.primeFactors, (if p ∣ m + (k + 1) then (1 : ℝ) else 0) / 2 ^ (k + 1) := by
      intro k
      rw [omega_mul_eq a _ ha (by omega), ← Finset.sum_div]
      ring
    rw [tsum_congr hpt, (hsA.add (hgeo.mul_left _)).tsum_sub (summable_sum hsI),
      hsA.tsum_add (hgeo.mul_left _), tsum_mul_left, h1, Summable.tsum_finsetSum hsI, mul_one]
  have tail_int : ∀ (q : ℕ) (z : ℤ), (q : ℝ) * ∑' n : ℕ, (ω n : ℝ) / 2 ^ n = z → ∀ m : ℕ,
      ∃ w : ℤ, (q : ℝ) * ∑' k : ℕ, (ω (m + (k + 1)) : ℝ) / 2 ^ (k + 1) = w := by
    intro q z hz m
    have hsum0 : Summable (fun n : ℕ => (ω n : ℝ) / 2 ^ n) := by
      have hbound : ∀ n : ℕ,
          (ω n : ℝ) / 2 ^ n ≤ (n : ℝ) ^ 1 * (1 / 2 : ℝ) ^ n + (1 / 2 : ℝ) ^ n := by
        intro n
        have h1 : ω n ≤ n + 1 := by
          rw [ArithmeticFunction.cardDistinctFactors_apply]
          calc n.primeFactorsList.dedup.length = n.primeFactors.card := rfl
            _ ≤ (Finset.range (n + 1)).card :=
                Finset.card_le_card (fun p hp =>
                  Finset.mem_range.2 (Nat.lt_succ_of_le (Nat.le_of_mem_primeFactors hp)))
            _ = n + 1 := Finset.card_range _
        have h2 : (ω n : ℝ) ≤ (n : ℝ) + 1 := by exact_mod_cast h1
        have h4 : (0 : ℝ) ≤ ((2 : ℝ) ^ n)⁻¹ := by positivity
        rw [pow_one, one_div, inv_pow, div_eq_mul_inv]
        nlinarith [mul_le_mul_of_nonneg_right h2 h4]
      refine Summable.of_nonneg_of_le (fun n => by positivity) hbound ?_
      exact (summable_pow_mul_geometric_of_norm_lt_one 1 (by norm_num [Real.norm_eq_abs])).add
        (summable_geometric_of_lt_one (by norm_num) (by norm_num))
    have h := hsum0.sum_add_tsum_nat_add (m + 1)
    have htail : ∑' j : ℕ, (ω (j + (m + 1)) : ℝ) / 2 ^ (j + (m + 1))
        = (∑' k : ℕ, (ω (m + (k + 1)) : ℝ) / 2 ^ (k + 1)) / 2 ^ m := by
      rw [← tsum_div_const]
      congr 1
      funext j
      rw [show j + (m + 1) = m + (j + 1) by ring, show m + (j + 1) = (j + 1) + m by ring, pow_add]
      rw [show (j + 1) + m = m + (j + 1) by ring]
      field_simp
    have hpow : ∀ i : ℕ, i ≤ m → (2 : ℝ) ^ (m - i) = 2 ^ m / 2 ^ i := fun i hi =>
      pow_sub₀ 2 (by norm_num) hi
    refine ⟨2 ^ m * z - (q : ℤ) * ∑ i ∈ Finset.range (m + 1), (ω i : ℤ) * 2 ^ (m - i), ?_⟩
    have hT : ∑' k : ℕ, (ω (m + (k + 1)) : ℝ) / 2 ^ (k + 1)
        = 2 ^ m * (∑' n : ℕ, (ω n : ℝ) / 2 ^ n - ∑ i ∈ Finset.range (m + 1), (ω i : ℝ) / 2 ^ i) := by
      rw [← h, htail]
      field_simp
      ring
    have hs2 : ∑ i ∈ Finset.range (m + 1), (ω i : ℝ) * 2 ^ (m - i)
        = 2 ^ m * ∑ i ∈ Finset.range (m + 1), (ω i : ℝ) / 2 ^ i := by
      rw [Finset.mul_sum]
      refine Finset.sum_congr rfl (fun i hi => ?_)
      rw [hpow i (Nat.lt_succ_iff.mp (Finset.mem_range.mp hi))]
      ring
    push_cast
    rw [hs2, ← hz, hT]
    ring
  have sum_I_le : ∀ (p Q T b : ℕ), Nat.Coprime p Q → 0 < p →
      ∑ t ∈ Finset.range T,
        ∑' k : ℕ, (if p ∣ b + Q * t + (k + 1) then (1 : ℝ) else 0) / 2 ^ (k + 1)
        ≤ (T : ℝ) / p + 1 := by
    intro p Q T b hcop hp
    have hgeo : Summable (fun k : ℕ => (1 : ℝ) / 2 ^ (k + 1)) := by
      refine (summable_geometric_two.mul_left (1 / 2 : ℝ)).congr (fun k => ?_)
      rw [one_div, one_div, ← inv_pow, pow_succ, mul_comm]
    have h1 : ∑' k : ℕ, (1 : ℝ) / 2 ^ (k + 1) = 1 := by
      calc ∑' k : ℕ, (1 : ℝ) / 2 ^ (k + 1) = ∑' n : ℕ, (1 : ℝ) / 2 / 2 ^ n :=
            tsum_congr (fun k => by ring)
        _ = 1 := tsum_geometric_two' 1
    have hsI : ∀ t ∈ Finset.range T,
        Summable (fun k : ℕ => (if p ∣ b + Q * t + (k + 1) then (1 : ℝ) else 0) / 2 ^ (k + 1)) := by
      intro t _
      refine Summable.of_nonneg_of_le (fun k => ?_) (fun k => ?_) hgeo
      · split_ifs <;> positivity
      · split_ifs
        · exact le_rfl
        · rw [zero_div]; positivity
    rw [← Summable.tsum_finsetSum hsI]
    have hbound : ∀ k : ℕ, ∑ t ∈ Finset.range T,
        (if p ∣ b + Q * t + (k + 1) then (1 : ℝ) else 0) / 2 ^ (k + 1)
          ≤ ((T / p + 1 : ℕ) : ℝ) * (1 / 2 ^ (k + 1)) := by
      intro k
      rw [← Finset.sum_div, Finset.sum_boole, mul_one_div]
      gcongr
      have hc := count_le p Q T (b + (k + 1)) hcop hp
      have e : (Finset.range T).filter (fun t => p ∣ b + Q * t + (k + 1))
          = (Finset.range T).filter (fun t => p ∣ b + (k + 1) + Q * t) := by
        apply Finset.filter_congr
        intro t _
        rw [show b + Q * t + (k + 1) = b + (k + 1) + Q * t by ring]
      rw [e]
      exact_mod_cast hc
    calc ∑' k : ℕ, ∑ t ∈ Finset.range T,
          (if p ∣ b + Q * t + (k + 1) then (1 : ℝ) else 0) / 2 ^ (k + 1)
        ≤ ∑' k : ℕ, ((T / p + 1 : ℕ) : ℝ) * (1 / 2 ^ (k + 1)) :=
          (summable_sum hsI).tsum_le_tsum hbound (hgeo.mul_left _)
      _ = ((T / p + 1 : ℕ) : ℝ) := by rw [tsum_mul_left, h1, mul_one]
      _ ≤ (T : ℝ) / p + 1 := by
          push_cast
          gcongr
          exact Nat.cast_div_le
  intro q z hz a Q b T ha hT hcop
  -- the mass of the primes of a dividing the shifted integers
  set I : ℕ → ℕ → ℝ := fun p m =>
    ∑' k : ℕ, (if p ∣ m + (k + 1) then (1 : ℝ) else 0) / 2 ^ (k + 1) with hI
  have hI0 : ∀ p m, 0 ≤ I p m := by
    intro p m
    exact tsum_nonneg (fun k => by split_ifs <;> positivity)
  have hpt : ∀ t : ℕ,
      |(q : ℝ) * ∑' k : ℕ, (ω (a * (b + Q * t + (k + 1))) : ℝ) / 2 ^ (k + 1)
        - round ((q : ℝ) * ∑' k : ℕ, (ω (a * (b + Q * t + (k + 1))) : ℝ) / 2 ^ (k + 1))|
      ≤ (q : ℝ) * ∑ p ∈ a.primeFactors, I p (b + Q * t) := by
    intro t
    obtain ⟨w, hw⟩ := tail_int q z hz (b + Q * t)
    have hd := dilated_tail a (b + Q * t) ha
    set x := (q : ℝ) * ∑' k : ℕ, (ω (a * (b + Q * t + (k + 1))) : ℝ) / 2 ^ (k + 1) with hx
    have hx' : x = ((w + q * ω a : ℤ) : ℝ) - (q : ℝ) * ∑ p ∈ a.primeFactors, I p (b + Q * t) := by
      rw [hx, hd]
      push_cast
      rw [← hw]
      simp only [hI]
      ring
    calc |x - round x| ≤ |x - ((w + q * ω a : ℤ) : ℝ)| := round_le x _
      _ = (q : ℝ) * ∑ p ∈ a.primeFactors, I p (b + Q * t) := by
          rw [hx', sub_sub_cancel_left, abs_neg, abs_of_nonneg]
          exact mul_nonneg (by positivity) (Finset.sum_nonneg (fun p _ => hI0 p _))
  have hTpos : (0 : ℝ) < T := by exact_mod_cast hT
  rw [div_le_iff₀ hTpos]
  calc ∑ t ∈ Finset.range T,
        |(q : ℝ) * ∑' k : ℕ, (ω (a * (b + Q * t + (k + 1))) : ℝ) / 2 ^ (k + 1)
          - round ((q : ℝ) * ∑' k : ℕ, (ω (a * (b + Q * t + (k + 1))) : ℝ) / 2 ^ (k + 1))|
      ≤ ∑ t ∈ Finset.range T, (q : ℝ) * ∑ p ∈ a.primeFactors, I p (b + Q * t) :=
        Finset.sum_le_sum (fun t _ => hpt t)
    _ = (q : ℝ) * ∑ p ∈ a.primeFactors, ∑ t ∈ Finset.range T, I p (b + Q * t) := by
        rw [← Finset.mul_sum, Finset.sum_comm]
    _ ≤ (q : ℝ) * ∑ p ∈ a.primeFactors, ((T : ℝ) / p + 1) := by
        gcongr with p hp
        have hpp : 0 < p := (Nat.prime_of_mem_primeFactors hp).pos
        have := sum_I_le p Q T b (hcop p hp) hpp
        simpa [hI, add_assoc] using this
    _ = ((q : ℝ) * ∑ p ∈ a.primeFactors, ((1 : ℝ) / p + 1 / T)) * T := by
        rw [mul_assoc, Finset.sum_mul]
        congr 1
        refine Finset.sum_congr rfl (fun p _ => ?_)
        field_simp
