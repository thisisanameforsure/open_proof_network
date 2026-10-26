import Mathlib

/- The divisor-counting function. -/
private def dd (n : ℕ) : ℕ := n.divisors.card

/- `b` times the "tail" `∑_{i ≥ 1} f(j+i) / 2^i`. -/
private noncomputable def Tail (f : ℕ → ℕ) (b : ℕ) (j : ℕ) : ℝ :=
  b * ∑' i : ℕ, (f (j + i + 1) : ℝ) / 2 ^ (i + 1)

/- The integer that the tail equals when the series is `a / b`. -/
private def Zint (f : ℕ → ℕ) (a : ℤ) (b : ℕ) (j : ℕ) : ℤ :=
  a * 2 ^ j - b * ∑ n ∈ Finset.range (j + 1), (f n : ℤ) * 2 ^ (j - n)

private lemma summable_shift {f : ℕ → ℕ} (hf : ∀ n, f n ≤ n) (j : ℕ) :
    Summable (fun i : ℕ => (f (j + i + 1) : ℝ) / 2 ^ (i + 1)) := by
  have h : Summable (fun i : ℕ => ((j + 1 : ℝ) + i) * (1/2) ^ i) := by
    have h1 := (summable_geometric_two).mul_left (j+1 : ℝ)
    have h2 := summable_pow_mul_geometric_of_norm_lt_one 1 (r := (1/2 : ℝ))
      (by norm_num [abs_of_pos])
    simpa [add_mul] using h1.add h2
  refine Summable.of_nonneg_of_le (fun i => by positivity) (fun i => ?_) h
  have : (f (j + i + 1) : ℝ) ≤ j + i + 1 := by exact_mod_cast hf _
  rw [div_eq_mul_inv, pow_succ, mul_inv, one_div, inv_pow]
  have : (0:ℝ) ≤ (2 ^ i)⁻¹ := by positivity
  nlinarith

private lemma tail_upper {f : ℕ → ℕ} (hf : ∀ n, f n ≤ n) (b j L : ℕ) :
    Tail f b j ≤ b * ∑ i ∈ Finset.range L, (f (j + i + 1) : ℝ) / 2 ^ (i + 1)
      + b * ((j + L + 2 : ℝ) / 2 ^ L) := by
  unfold Tail
  rw [← (summable_shift hf j).sum_add_tsum_nat_add L, mul_add]
  gcongr
  have hg1 : Summable (fun i : ℕ => (1/2 : ℝ) ^ i) := summable_geometric_two
  have hg2 : Summable (fun i : ℕ => (i : ℝ) * (1/2 : ℝ) ^ i) := by
    simpa using summable_pow_mul_geometric_of_norm_lt_one 1 (r := (1/2 : ℝ))
      (by norm_num [abs_of_pos])
  have key : ∑' i : ℕ, ((j + L + 1 : ℝ) / 2 ^ (L + 1) * (1/2) ^ i
      + 1 / 2 ^ (L + 1) * ((i : ℝ) * (1/2) ^ i)) = (j + L + 2 : ℝ) / 2 ^ L := by
    rw [(hg1.mul_left _).tsum_add (hg2.mul_left _), tsum_mul_left, tsum_mul_left,
      tsum_geometric_two, tsum_coe_mul_geometric_of_norm_lt_one (by norm_num [abs_of_pos])]
    rw [pow_succ]; field_simp; ring
  rw [← key]
  refine Summable.tsum_le_tsum (fun i => ?_) ((summable_nat_add_iff L).mpr (summable_shift hf j))
    ((hg1.mul_left _).add (hg2.mul_left _))
  have : (f (j + (i + L) + 1) : ℝ) ≤ j + L + 1 + i := by
    have := hf (j + (i + L) + 1)
    have : (f (j + (i + L) + 1) : ℝ) ≤ ((j + (i + L) + 1 : ℕ) : ℝ) := by exact_mod_cast this
    push_cast at this; linarith
  show (f (j + (i + L) + 1) : ℝ) / 2 ^ (i + L + 1) ≤ _
  rw [show (2:ℝ) ^ (i + L + 1) = 2 ^ (L+1) * 2 ^ i by ring, one_div_pow]
  rw [div_le_iff₀ (by positivity)]
  field_simp
  linarith

private lemma dd_le_two_mul_small (n : ℕ) :
    dd n ≤ 2 * (n.divisors.filter (fun e => e * e ≤ n)).card := by
  unfold dd
  rw [← Finset.card_filter_add_card_filter_not (fun e => e * e ≤ n)]
  have : (n.divisors.filter (fun e => ¬ e * e ≤ n)).card ≤
      (n.divisors.filter (fun e => e * e ≤ n)).card := by
    apply Finset.card_le_card_of_injOn (fun e => n / e)
    · intro e he
      simp only [Finset.coe_filter, Nat.mem_divisors, not_le, Set.mem_setOf_eq] at he ⊢
      obtain ⟨⟨hd, hn⟩, hlt⟩ := he
      have hepos : 0 < e := Nat.pos_of_dvd_of_pos hd (Nat.pos_of_ne_zero hn)
      refine ⟨⟨Nat.div_dvd_of_dvd hd, hn⟩, ?_⟩
      have h1 : n / e < e := (Nat.div_lt_iff_lt_mul hepos).mpr hlt
      calc n / e * (n / e) ≤ n / e * e := Nat.mul_le_mul_left _ h1.le
        _ = n := Nat.div_mul_cancel hd
    · intro e1 h1 e2 h2 h
      simp only [Finset.coe_filter, Nat.mem_divisors, Set.mem_setOf_eq] at h1 h2
      have := congrArg (fun x => n / x) h
      simp only at this
      rwa [Nat.div_div_self h1.1.1 h1.1.2, Nat.div_div_self h2.1.1 h2.1.2] at this
  omega

private lemma card_AP_dvd_le (r Q X e : ℕ) (hcop : Nat.Coprime r Q) :
    ((Finset.range X).filter (fun t => (e + 1) ∣ r + t * Q)).card ≤ X / (e + 1) + 1 := by
  set E := e + 1 with hE
  have hEpos : 0 < E := by omega
  have key : ∀ t1 ∈ (Finset.range X).filter (fun t => E ∣ r + t * Q),
      ∀ t2 ∈ (Finset.range X).filter (fun t => E ∣ r + t * Q), t1 / E = t2 / E → t1 ≤ t2 → t1 = t2 := by
    intro t1 h1 t2 h2 hq hle
    simp only [Finset.mem_filter, Finset.mem_range] at h1 h2
    have hcopE : Nat.Coprime E Q := by
      have hg1 : Nat.gcd E Q ∣ r + t1 * Q := (Nat.gcd_dvd_left E Q).trans h1.2
      have hg2 : Nat.gcd E Q ∣ t1 * Q := Dvd.dvd.mul_left (Nat.gcd_dvd_right E Q) _
      have hg3 : Nat.gcd E Q ∣ r := (Nat.dvd_add_left hg2).mp hg1
      have hg4 : Nat.gcd E Q ∣ Nat.gcd r Q := Nat.dvd_gcd hg3 (Nat.gcd_dvd_right E Q)
      rw [hcop] at hg4
      exact Nat.dvd_one.mp hg4
    have hd : E ∣ (t2 - t1) * Q := by
      have := Nat.dvd_sub h2.2 h1.2
      rwa [show r + t2 * Q - (r + t1 * Q) = (t2 - t1) * Q by rw [Nat.sub_mul]; omega] at this
    have hd2 : E ∣ t2 - t1 := hcopE.dvd_of_dvd_mul_right hd
    have hlt : t2 - t1 < E := by
      have e1 := Nat.div_add_mod t1 E
      have e2 := Nat.div_add_mod t2 E
      have m1 := Nat.mod_lt t1 hEpos
      have m2 := Nat.mod_lt t2 hEpos
      rw [hq] at e1
      omega
    have := Nat.eq_zero_of_dvd_of_lt hd2 hlt
    omega
  calc ((Finset.range X).filter (fun t => E ∣ r + t * Q)).card ≤ (Finset.range (X / E + 1)).card := by
        apply Finset.card_le_card_of_injOn (fun t => t / E)
        · intro t ht
          simp only [Finset.coe_filter, Finset.mem_range, Set.mem_setOf_eq] at ht
          simp only [Finset.coe_range, Set.mem_Iio]
          have := Nat.div_le_div_right (c := E) ht.1.le
          omega
        · intro t1 h1 t2 h2 hq
          rcases le_total t1 t2 with h | h
          · exact key t1 h1 t2 h2 hq h
          · exact (key t2 h2 t1 h1 hq.symm h).symm
    _ = X / E + 1 := Finset.card_range _

private lemma sum_dd_AP_le (r Q X : ℕ) (hcop : Nat.Coprime r Q)
    (hX : ∀ t < X, r + t * Q ≤ X * X) :
    (∑ t ∈ Finset.range X, (dd (r + t * Q) : ℝ)) ≤ 2 * X * (2 + Real.log X) := by
  have hnat : ∑ t ∈ Finset.range X, dd (r + t * Q) ≤ 2 * ∑ e ∈ Finset.range X, (X / (e + 1) + 1) := by
    calc ∑ t ∈ Finset.range X, dd (r + t * Q)
        ≤ ∑ t ∈ Finset.range X, 2 * ((Finset.range X).filter (fun e => (e + 1) ∣ r + t * Q)).card := by
          apply Finset.sum_le_sum; intro t ht
          refine (dd_le_two_mul_small _).trans ?_
          apply Nat.mul_le_mul_left
          apply Finset.card_le_card_of_injOn (fun e => e - 1)
          · intro e he
            simp only [Finset.coe_filter, Nat.mem_divisors, Set.mem_setOf_eq] at he
            simp only [Finset.coe_filter, Finset.mem_range, Set.mem_setOf_eq]
            have hepos : 0 < e := Nat.pos_of_dvd_of_pos he.1.1 (Nat.pos_of_ne_zero he.1.2)
            have : e * e ≤ X * X := he.2.trans (hX t (by simpa using ht))
            have : e ≤ X := Nat.mul_self_le_mul_self_iff.mp this
            refine ⟨by omega, ?_⟩
            rw [Nat.sub_add_cancel hepos]; exact he.1.1
          · intro e1 h1 e2 h2 h
            simp only [Finset.coe_filter, Nat.mem_divisors, Set.mem_setOf_eq] at h1 h2
            have := Nat.pos_of_dvd_of_pos h1.1.1 (Nat.pos_of_ne_zero h1.1.2)
            have := Nat.pos_of_dvd_of_pos h2.1.1 (Nat.pos_of_ne_zero h2.1.2)
            simp only at h
            omega
      _ = 2 * ∑ e ∈ Finset.range X, ((Finset.range X).filter (fun t => (e + 1) ∣ r + t * Q)).card := by
          rw [← Finset.mul_sum]
          congr 1
          simp only [Finset.card_filter]
          exact Finset.sum_comm
      _ ≤ 2 * ∑ e ∈ Finset.range X, (X / (e + 1) + 1) := by
          apply Nat.mul_le_mul_left
          exact Finset.sum_le_sum fun e _ => card_AP_dvd_le r Q X e hcop
  have hreal : ((∑ e ∈ Finset.range X, (X / (e + 1) + 1) : ℕ) : ℝ) ≤ X * (1 + Real.log X) + X := by
    push_cast
    rw [Finset.sum_add_distrib]
    simp only [Finset.sum_const, Finset.card_range, nsmul_eq_mul, mul_one]
    gcongr
    calc ∑ e ∈ Finset.range X, ((X / (e + 1) : ℕ) : ℝ) ≤ ∑ e ∈ Finset.range X, (X : ℝ) / (e + 1) := by
          apply Finset.sum_le_sum; intro e _
          have := Nat.cast_div_le (α := ℝ) (m := X) (n := e + 1)
          push_cast at this; exact this
      _ = X * (harmonic X : ℝ) := by
          rw [harmonic]; push_cast; rw [Finset.mul_sum]
          apply Finset.sum_congr rfl; intro e _; field_simp
      _ ≤ X * (1 + Real.log X) := by
          gcongr
          exact harmonic_le_one_add_log X
  have h1 : (∑ t ∈ Finset.range X, (dd (r + t * Q) : ℝ)) ≤
      2 * ((∑ e ∈ Finset.range X, (X / (e + 1) + 1) : ℕ) : ℝ) := by
    exact_mod_cast hnat
  linarith


/- Submultiplicativity of the divisor count. -/
private lemma dd_mul_le (a b : ℕ) : dd (a * b) ≤ dd a * dd b := by
  unfold dd
  rw [Nat.divisors_mul]
  exact Finset.card_mul_le

private lemma dd_le_of_dvd {a b : ℕ} (hb : b ≠ 0) (h : a ∣ b) : dd a ≤ dd b :=
  Finset.card_le_card (Nat.divisors_subset_of_dvd hb h)

/- The divisor sum along a progression with any start, in terms of the gcd. -/
private lemma sum_dd_AP_le' (r Q X : ℕ) (hQ : 0 < Q)
    (hX : ∀ t < X, r + t * Q ≤ X * X) :
    (∑ t ∈ Finset.range X, (dd (r + t * Q) : ℝ)) ≤ dd (Nat.gcd r Q) * (2 * X * (2 + Real.log X)) := by
  set g := Nat.gcd r Q with hg
  have hgpos : 0 < g := Nat.gcd_pos_of_pos_right _ hQ
  obtain ⟨r', hr'⟩ : g ∣ r := Nat.gcd_dvd_left r Q
  obtain ⟨Q', hQ'⟩ : g ∣ Q := Nat.gcd_dvd_right r Q
  have hcop : Nat.Coprime r' Q' := by
    have h := Nat.coprime_div_gcd_div_gcd (m := r) (n := Q) hgpos
    have e1 : r / g = r' := by
      rw [hr']
      exact Nat.mul_div_cancel_left r' hgpos
    have e2 : Q / g = Q' := by
      rw [hQ']
      exact Nat.mul_div_cancel_left Q' hgpos
    rwa [e1, e2] at h
  have hsplit : ∀ t, r + t * Q = g * (r' + t * Q') := by
    intro t
    rw [hr', hQ']
    ring
  calc (∑ t ∈ Finset.range X, (dd (r + t * Q) : ℝ))
      ≤ ∑ t ∈ Finset.range X, (dd g : ℝ) * dd (r' + t * Q') := by
        apply Finset.sum_le_sum; intro t _
        rw [hsplit]; exact_mod_cast dd_mul_le _ (r' + t * Q')
    _ = dd g * ∑ t ∈ Finset.range X, (dd (r' + t * Q') : ℝ) := by rw [Finset.mul_sum]
    _ ≤ dd g * (2 * X * (2 + Real.log X)) := by
        gcongr
        apply sum_dd_AP_le r' Q' X hcop
        intro t ht
        have h := hX t ht
        rw [hsplit] at h
        calc r' + t * Q' ≤ g * (r' + t * Q') := Nat.le_mul_of_pos_left _ hgpos
          _ ≤ X * X := h

/- A geometric tail starting at `s` is at most `1`. -/
private lemma geom_tail_le (s L : ℕ) :
    ∑ i ∈ Finset.range L, (if s ≤ i then (1 / 2 : ℝ) ^ (i + 1 - s) else 0) ≤ 1 := by
  have hgeom : ∀ L : ℕ, ∑ i ∈ Finset.range L, (1 / 2 : ℝ) ^ (i + 1) ≤ 1 := by
    intro L
    have : ∑ i ∈ Finset.range L, (1 / 2 : ℝ) ^ (i + 1) = 1 - (1 / 2) ^ L := by
      induction L with
      | zero => simp
      | succ n ih => rw [Finset.sum_range_succ, ih]; ring
    rw [this]; linarith [pow_pos (by norm_num : (0 : ℝ) < 1 / 2) L]
  calc ∑ i ∈ Finset.range L, (if s ≤ i then (1 / 2 : ℝ) ^ (i + 1 - s) else 0)
      ≤ ∑ i ∈ Finset.range (s + L), (if s ≤ i then (1 / 2 : ℝ) ^ (i + 1 - s) else 0) := by
        apply Finset.sum_le_sum_of_subset_of_nonneg
        · exact Finset.range_mono (Nat.le_add_left L s)
        · intro i _ _; split_ifs <;> positivity
    _ = ∑ i ∈ Finset.range s, (if s ≤ i then (1 / 2 : ℝ) ^ (i + 1 - s) else 0)
          + ∑ j ∈ Finset.range L, (if s ≤ s + j then (1 / 2 : ℝ) ^ (s + j + 1 - s) else 0) :=
        Finset.sum_range_add _ s L
    _ = 0 + ∑ j ∈ Finset.range L, (1 / 2 : ℝ) ^ (j + 1) := by
        congr 1
        · apply Finset.sum_eq_zero
          intro i hi
          rw [if_neg (by simp at hi; omega)]
        · apply Finset.sum_congr rfl
          intro j _
          rw [if_pos (by omega), show s + j + 1 - s = j + 1 by omega]
    _ ≤ 1 := by rw [zero_add]; exact hgeom L

/- The averaging contradiction with weights: the progression starts `c + m + i + 1` need only be
coprime to `Q` for `m + i < p₀`; for the others the gcd's divisor count is at most `D ≤ 2^(p₀-m)`. -/
private lemma averaging_contra2 {f : ℕ → ℕ} (hfdd : ∀ n, f n ≤ dd n)
    {b m q Q c p₀ D : ℕ} (hb : 0 < b) (hQpos : 0 < Q) (hcQ : c < Q)
    (hQle : Q ≤ 2 ^ q) (hA2 : m + 3 * q ≤ 2 ^ q) (hA3 : 8 * b ≤ 2 ^ q)
    (hA4 : 4 * b * (3 + q) + 1 < 2 ^ m) (hmp : m ≤ p₀) (hD : D ≤ 2 ^ (p₀ - m))
    (hcop : ∀ i < 3 * q, m + i < p₀ → Nat.Coprime (c + m + i + 1) Q)
    (hgcd : ∀ i < 3 * q, dd (Nat.gcd (c + m + i + 1) Q) ≤ D)
    (hlow : ∀ t, (2 : ℝ) ^ m ≤ Tail f b (c + t * Q + m)) : False := by
  have hf : ∀ n, f n ≤ n := fun n => (hfdd n).trans (Nat.card_divisors_le_self n)
  set L := 3 * q with hLdef
  set X := Q + m + L with hXdef
  have hX1 : 1 ≤ X := by omega
  have hXpow : X ≤ 2 ^ (q + 1) := by rw [pow_succ]; omega
  have hLX : 2 * b * X ^ 2 ≤ 2 ^ L := by
    calc 2 * b * X ^ 2 ≤ 2 * b * (2 ^ (q + 1)) ^ 2 := by gcongr
      _ = 8 * b * (2 ^ q * 2 ^ q) := by ring
      _ ≤ 2 ^ q * (2 ^ q * 2 ^ q) := by gcongr
      _ = 2 ^ L := by rw [hLdef]; ring
  have hrange : ∀ t < X, c + t * Q < X * Q := by
    intro t ht
    have : (t + 1) * Q ≤ X * Q := Nat.mul_le_mul_right _ ht
    nlinarith
  have hXX : X * Q + m + L ≤ X * X := by
    have : X * X = X * Q + X * (m + L) := by rw [hXdef]; ring
    have : m + L ≤ X * (m + L) := Nat.le_mul_of_pos_left _ hX1
    omega
  have hupt : ∀ t < X, Tail f b (c + t * Q + m) ≤
      b * ∑ i ∈ Finset.range L, (f (c + m + i + 1 + t * Q) : ℝ) / 2 ^ (i + 1)
        + b * ((2 * X ^ 2 : ℕ) / 2 ^ L : ℝ) := by
    intro t ht
    have h := tail_upper hf b (c + t * Q + m) L
    have e : ∀ i, c + t * Q + m + i + 1 = c + m + i + 1 + t * Q := fun i => by ring
    simp only [e] at h
    refine h.trans (add_le_add le_rfl ?_)
    gcongr
    have := hrange t ht
    have h2 : c + t * Q + m + L + 2 ≤ 2 * X ^ 2 := by nlinarith
    exact_mod_cast h2
  set B : ℝ := 2 * X * (2 + Real.log X) with hBdef
  have hB0 : 0 ≤ B := by
    have : 0 ≤ Real.log X := Real.log_nonneg (by exact_mod_cast hX1)
    positivity
  -- the weight of position `i`
  set w : ℕ → ℝ := fun i => if m + i < p₀ then 1 else D with hw
  have hF : ∀ i ∈ Finset.range L, (∑ t ∈ Finset.range X, (f (c + m + i + 1 + t * Q) : ℝ)) ≤ w i * B := by
    intro i hi
    have hiL : i < L := by simpa using hi
    have hXi : ∀ t < X, c + m + i + 1 + t * Q ≤ X * X := by
      intro t ht
      have := hrange t ht
      omega
    calc (∑ t ∈ Finset.range X, (f (c + m + i + 1 + t * Q) : ℝ))
        ≤ ∑ t ∈ Finset.range X, (dd (c + m + i + 1 + t * Q) : ℝ) :=
          Finset.sum_le_sum fun t _ => by exact_mod_cast hfdd (c + m + i + 1 + t * Q)
      _ ≤ w i * B := by
          simp only [hw]
          split_ifs with hip
          · rw [one_mul]
            exact sum_dd_AP_le _ _ _ (hcop i hiL hip) hXi
          · calc (∑ t ∈ Finset.range X, (dd (c + m + i + 1 + t * Q) : ℝ))
                ≤ dd (Nat.gcd (c + m + i + 1) Q) * B := sum_dd_AP_le' _ _ _ hQpos hXi
              _ ≤ D * B := by gcongr; exact_mod_cast hgcd i hiL
  -- the weighted geometric sum is at most 2
  have hwsum : ∑ i ∈ Finset.range L, w i * (1 / 2 : ℝ) ^ (i + 1) ≤ 2 := by
    have hgeom : ∀ L : ℕ, ∑ i ∈ Finset.range L, (1 / 2 : ℝ) ^ (i + 1) ≤ 1 := by
      intro L
      have : ∑ i ∈ Finset.range L, (1 / 2 : ℝ) ^ (i + 1) = 1 - (1 / 2) ^ L := by
        induction L with
        | zero => simp
        | succ n ih => rw [Finset.sum_range_succ, ih]; ring
      rw [this]; linarith [pow_pos (by norm_num : (0 : ℝ) < 1 / 2) L]
    have hterm : ∀ i, w i * (1 / 2 : ℝ) ^ (i + 1) ≤
        (1 / 2 : ℝ) ^ (i + 1) + (if p₀ - m ≤ i then (1 / 2 : ℝ) ^ (i + 1 - (p₀ - m)) else 0) := by
      intro i
      simp only [hw]
      split_ifs with h1 h2
      · rw [one_mul]; linarith [pow_pos (by norm_num : (0 : ℝ) < 1 / 2) (i + 1 - (p₀ - m))]
      · rw [one_mul, add_zero]
      · have hD' : (D : ℝ) ≤ 2 ^ (p₀ - m) := by exact_mod_cast hD
        have hpow : (1 / 2 : ℝ) ^ (i + 1) =
            (1 / 2 : ℝ) ^ (i + 1 - (p₀ - m)) * (1 / 2 : ℝ) ^ (p₀ - m) := by
          rw [← pow_add]; congr 1; omega
        have hDb : (D : ℝ) * (1 / 2 : ℝ) ^ (p₀ - m) ≤ 1 := by
          rw [one_div_pow, mul_one_div, div_le_one (by positivity)]; exact hD'
        have ha : (0 : ℝ) ≤ (1 / 2 : ℝ) ^ (i + 1 - (p₀ - m)) := by positivity
        calc (D : ℝ) * (1 / 2 : ℝ) ^ (i + 1)
            = (1 / 2 : ℝ) ^ (i + 1 - (p₀ - m)) * ((D : ℝ) * (1 / 2 : ℝ) ^ (p₀ - m)) := by
              rw [hpow]; ring
          _ ≤ (1 / 2 : ℝ) ^ (i + 1 - (p₀ - m)) * 1 := by gcongr
          _ ≤ (1 / 2 : ℝ) ^ (i + 1) + (1 / 2 : ℝ) ^ (i + 1 - (p₀ - m)) := by
              rw [mul_one]; linarith [pow_pos (by norm_num : (0 : ℝ) < 1 / 2) (i + 1)]
      · omega
    calc ∑ i ∈ Finset.range L, w i * (1 / 2 : ℝ) ^ (i + 1)
        ≤ ∑ i ∈ Finset.range L, ((1 / 2 : ℝ) ^ (i + 1)
            + (if p₀ - m ≤ i then (1 / 2 : ℝ) ^ (i + 1 - (p₀ - m)) else 0)) :=
          Finset.sum_le_sum fun i _ => hterm i
      _ = ∑ i ∈ Finset.range L, (1 / 2 : ℝ) ^ (i + 1)
            + ∑ i ∈ Finset.range L, (if p₀ - m ≤ i then (1 / 2 : ℝ) ^ (i + 1 - (p₀ - m)) else 0) :=
          Finset.sum_add_distrib
      _ ≤ 1 + 1 := add_le_add (hgeom L) (geom_tail_le _ _)
      _ = 2 := by norm_num
  have hmain : (X : ℝ) * 2 ^ m ≤ b * (2 * B) + X := by
    calc (X : ℝ) * 2 ^ m = ∑ t ∈ Finset.range X, (2 : ℝ) ^ m := by simp
      _ ≤ ∑ t ∈ Finset.range X, Tail f b (c + t * Q + m) := Finset.sum_le_sum fun t _ => hlow t
      _ ≤ ∑ t ∈ Finset.range X, (b * ∑ i ∈ Finset.range L, (f (c + m + i + 1 + t * Q) : ℝ) / 2 ^ (i + 1)
            + b * ((2 * X ^ 2 : ℕ) / 2 ^ L : ℝ)) :=
          Finset.sum_le_sum fun t ht => hupt t (by simpa using ht)
      _ = b * ∑ i ∈ Finset.range L, (∑ t ∈ Finset.range X, (f (c + m + i + 1 + t * Q) : ℝ)) * (1 / 2) ^ (i + 1)
            + X * (b * ((2 * X ^ 2 : ℕ) / 2 ^ L : ℝ)) := by
          rw [Finset.sum_add_distrib, ← Finset.mul_sum, Finset.sum_comm]
          simp only [Finset.sum_const, Finset.card_range, nsmul_eq_mul, Finset.sum_mul, div_eq_mul_inv,
            inv_pow, one_mul]
      _ ≤ b * ∑ i ∈ Finset.range L, (w i * B) * (1 / 2) ^ (i + 1) + X * 1 := by
          apply add_le_add
          · apply mul_le_mul_of_nonneg_left _ (Nat.cast_nonneg _)
            apply Finset.sum_le_sum
            intro i hi
            exact mul_le_mul_of_nonneg_right (hF i hi) (by positivity)
          · apply mul_le_mul_of_nonneg_left _ (Nat.cast_nonneg _)
            rw [← mul_div_assoc, div_le_one (by positivity)]
            have h1 : b * (2 * X ^ 2) ≤ 2 ^ L := by
              calc b * (2 * X ^ 2) = 2 * b * X ^ 2 := by ring
                _ ≤ 2 ^ L := hLX
            exact_mod_cast h1
      _ ≤ b * (2 * B) + X := by
          rw [mul_one]
          apply add_le_add_left
          apply mul_le_mul_of_nonneg_left _ (Nat.cast_nonneg _)
          calc ∑ i ∈ Finset.range L, (w i * B) * (1 / 2 : ℝ) ^ (i + 1)
              = B * ∑ i ∈ Finset.range L, w i * (1 / 2 : ℝ) ^ (i + 1) := by
                rw [Finset.mul_sum]; apply Finset.sum_congr rfl; intro i _; ring
            _ ≤ B * 2 := mul_le_mul_of_nonneg_left hwsum hB0
            _ = 2 * B := mul_comm _ _
  have hXpos : (0 : ℝ) < X := by exact_mod_cast hX1
  have h2m : (2 : ℝ) ^ m ≤ 4 * b * (2 + Real.log X) + 1 := by
    have : (X : ℝ) * 2 ^ m ≤ X * (4 * b * (2 + Real.log X) + 1) := by
      rw [hBdef] at hmain; nlinarith
    exact le_of_mul_le_mul_left this hXpos
  have hlogX : Real.log X ≤ q + 1 := by
    calc Real.log X ≤ Real.log ((2 : ℝ) ^ (q + 1)) :=
          Real.log_le_log hXpos (by exact_mod_cast hXpow)
      _ = (q + 1) * Real.log 2 := by rw [Real.log_pow]; push_cast; ring
      _ ≤ (q + 1) * 1 := by
          gcongr
          linarith [Real.log_two_lt_d9]
      _ = q + 1 := mul_one _
  have hA4' : (4 * b * (3 + q) + 1 : ℝ) < 2 ^ m := by exact_mod_cast hA4
  have : (4 * b * (2 + Real.log X) + 1 : ℝ) ≤ 4 * b * (3 + q) + 1 := by
    have : (0 : ℝ) ≤ b := by positivity
    nlinarith
  linarith

theorem weight_test_end : True := trivial
