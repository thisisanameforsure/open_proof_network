import Mathlib

theorem Opn.erdos_69_correction_mean_le :
    ∀ (a Q b T : ℕ), 0 < T → (∀ p ∈ a.primeFactors, Nat.Coprime p Q) →
      (∑ t ∈ Finset.range T, ∑ p ∈ a.primeFactors,
          ∑' k : ℕ, (if p ∣ b + Q * t + (k + 1) then (1 : ℝ) else 0) / 2 ^ (k + 1)) / T
        ≤ ∑ p ∈ a.primeFactors, ((1 : ℝ) / p + 1 / T) := by
  intro a Q b T hT hcop
  have hcount : ∀ (p Q c T : ℕ), p.Prime → Nat.Coprime p Q →
      ((Finset.range T).filter (fun t => p ∣ c + Q * t)).card ≤ T / p + 1 := by
    intro p Q c T hp hQ
    have hp0 : 0 < p := hp.pos
    have key := Finset.card_le_card_of_injOn (s := (Finset.range T).filter (fun t => p ∣ c + Q * t))
      (t := Finset.range (T / p + 1)) (fun t => t / p) ?_ ?_
    · simpa using key
    · intro t ht
      have ht1 : t < T := (Finset.mem_range.1 (Finset.mem_filter.1 ht).1)
      exact Finset.mem_coe.2 (Finset.mem_range.2 (Nat.lt_succ_of_le (Nat.div_le_div_right ht1.le)))
    · intro t ht t' ht' heq
      have ht := Finset.mem_filter.1 (Finset.mem_coe.1 ht)
      have ht' := Finset.mem_filter.1 (Finset.mem_coe.1 ht')
      rw [Finset.mem_range] at ht ht'
      have heq' : t / p = t' / p := heq
      -- p ∣ Q * (t - t') in ℤ
      have hz : (p : ℤ) ∣ (Q : ℤ) * ((t : ℤ) - t') := by
        have h1 : (p : ℤ) ∣ (c : ℤ) + Q * t := by exact_mod_cast ht.2
        have h2 : (p : ℤ) ∣ (c : ℤ) + Q * t' := by exact_mod_cast ht'.2
        have := dvd_sub h1 h2
        have e : (c : ℤ) + Q * t - (c + Q * t') = Q * (t - t') := by ring
        rwa [e] at this
      have hpQ : ¬ (p : ℤ) ∣ Q := by
        intro h
        have : p ∣ Q := by exact_mod_cast h
        have := Nat.Coprime.eq_one_of_dvd hQ this
        exact hp.one_lt.ne' this
      have hpd : (p : ℤ) ∣ (t : ℤ) - t' :=
        (Int.Prime.dvd_mul' hp hz).resolve_left hpQ
      -- |t - t'| < p
      have hlt1 : (t : ℤ) - t' < p := by
        have a1 := Nat.div_add_mod t p
        have a2 := Nat.div_add_mod t' p
        have b1 := Nat.mod_lt t hp0
        have b2 := Nat.mod_lt t' hp0
        rw [heq'] at a1
        omega
      have hlt2 : (t' : ℤ) - t < p := by
        have a1 := Nat.div_add_mod t p
        have a2 := Nat.div_add_mod t' p
        have b1 := Nat.mod_lt t hp0
        have b2 := Nat.mod_lt t' hp0
        rw [heq'] at a1
        omega
      obtain ⟨k, hk⟩ := hpd
      have hp' : (0 : ℤ) < p := by exact_mod_cast hp0
      have : k = 0 := by
        rcases lt_trichotomy k 0 with h | h | h
        · nlinarith
        · exact h
        · nlinarith
      rw [this, mul_zero] at hk
      omega
  have hTpos : (0 : ℝ) < T := by exact_mod_cast hT
  have hS2 : Summable (fun k : ℕ => (1 : ℝ) / 2 ^ (k + 1)) := by
    refine Summable.of_nonneg_of_le (fun k => by positivity) (fun k => ?_)
      (summable_geometric_of_lt_one (by norm_num : (0 : ℝ) ≤ 1 / 2) (by norm_num))
    rw [one_div_pow, pow_succ]
    apply one_div_le_one_div_of_le (by positivity)
    linarith [pow_pos (by norm_num : (0 : ℝ) < 2) k]
  have hsum1 : ∑' k : ℕ, (1 : ℝ) / 2 ^ (k + 1) = 1 := by
    have : (fun k : ℕ => (1 : ℝ) / 2 ^ (k + 1)) = fun k => (1 / 2) * (1 / 2 : ℝ) ^ k := by
      funext k; rw [pow_succ, one_div_pow]; field_simp
    rw [this, tsum_mul_left, tsum_geometric_two]; norm_num
  have hind : ∀ (p t : ℕ), Summable (fun k : ℕ =>
      (if p ∣ b + Q * t + (k + 1) then (1 : ℝ) else 0) / 2 ^ (k + 1)) := by
    intro p t
    refine Summable.of_nonneg_of_le (fun k => by split_ifs <;> positivity) (fun k => ?_) hS2
    split_ifs <;> simp
  -- one prime at a time
  have hper : ∀ p ∈ a.primeFactors, ∑ t ∈ Finset.range T,
      ∑' k : ℕ, (if p ∣ b + Q * t + (k + 1) then (1 : ℝ) else 0) / 2 ^ (k + 1)
        ≤ (T : ℝ) / p + 1 := by
    intro p hp
    have hpp : p.Prime := Nat.prime_of_mem_primeFactors hp
    have hppos : (0 : ℝ) < p := by exact_mod_cast hpp.pos
    rw [← Summable.tsum_finsetSum (fun t _ => hind p t)]
    have hk : ∀ k : ℕ, ∑ t ∈ Finset.range T,
        (if p ∣ b + Q * t + (k + 1) then (1 : ℝ) else 0) / 2 ^ (k + 1)
          ≤ ((T : ℝ) / p + 1) * (1 / 2 ^ (k + 1)) := by
      intro k
      rw [← Finset.sum_div, Finset.sum_boole]
      have hc := hcount p Q (b + (k + 1)) T hpp (hcop p hp)
      have hfe : (Finset.range T).filter (fun t => p ∣ b + Q * t + (k + 1))
          = (Finset.range T).filter (fun t => p ∣ b + (k + 1) + Q * t) := by
        apply Finset.filter_congr
        intro t _
        rw [show b + Q * t + (k + 1) = b + (k + 1) + Q * t by ring]
      rw [hfe]
      have hc' : (((Finset.range T).filter (fun t => p ∣ b + (k + 1) + Q * t)).card : ℝ)
          ≤ (T : ℝ) / p + 1 := by
        have h1 : ((T / p : ℕ) : ℝ) ≤ (T : ℝ) / p := Nat.cast_div_le
        have h2 : (((Finset.range T).filter (fun t => p ∣ b + (k + 1) + Q * t)).card : ℝ)
            ≤ ((T / p : ℕ) : ℝ) + 1 := by exact_mod_cast hc
        linarith
      rw [div_eq_mul_one_div]
      exact mul_le_mul_of_nonneg_right hc' (by positivity)
    calc ∑' k : ℕ, ∑ t ∈ Finset.range T,
          (if p ∣ b + Q * t + (k + 1) then (1 : ℝ) else 0) / 2 ^ (k + 1)
        ≤ ∑' k : ℕ, ((T : ℝ) / p + 1) * (1 / 2 ^ (k + 1)) :=
          Summable.tsum_le_tsum hk (summable_sum (fun t _ => hind p t)) (hS2.mul_left _)
      _ = (T : ℝ) / p + 1 := by rw [tsum_mul_left, hsum1, mul_one]
  rw [div_le_iff₀ hTpos, Finset.sum_comm, Finset.sum_mul]
  refine Finset.sum_le_sum (fun p hp => ?_)
  have hppos : (0 : ℝ) < p := by exact_mod_cast (Nat.prime_of_mem_primeFactors hp).pos
  calc ∑ t ∈ Finset.range T,
        ∑' k : ℕ, (if p ∣ b + Q * t + (k + 1) then (1 : ℝ) else 0) / 2 ^ (k + 1)
      ≤ (T : ℝ) / p + 1 := hper p hp
    _ = ((1 : ℝ) / p + 1 / T) * T := by field_simp
