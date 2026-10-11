import Mathlib

/-- Lemma I (the configuration B = {2p} ∪ T is impossible): a set T of positive integers, none a
multiple of p, odd members < n, even members < 2n, every (even b, odd t) pair with b < n·gcd(b,t),
has at most n − 2 members.  (2p < n ≤ 3p, p an odd prime.) -/
theorem R2b.lemI (n p : ℕ) (T : Finset ℕ) (hp : p.Prime) (hp3 : 3 ≤ p) (h2p : 2 * p < n)
    (hn3 : n ≤ 3 * p)
    (h0 : ∀ b ∈ T, 0 < b) (hpT : ∀ b ∈ T, ¬ p ∣ b)
    (ho : ∀ b ∈ T, ¬ 2 ∣ b → b < n) (he : ∀ b ∈ T, 2 ∣ b → b < 2 * n)
    (hx : ∀ b ∈ T, ∀ t ∈ T, 2 ∣ b → ¬ 2 ∣ t → b < n * b.gcd t) :
    T.card + 2 ≤ n := by
  -- φ t = the unique t·2^j in [n/2, n-1]
  have hφ : ∀ b : ℕ, 0 < b → b < n →
      b * 2 ^ Nat.log 2 ((n - 1) / b) ≤ n - 1 ∧ n - 1 < 2 * (b * 2 ^ Nat.log 2 ((n - 1) / b)) := by
    intro b hb hbn
    have hne : (n - 1) / b ≠ 0 := by
      have : 0 < (n - 1) / b := Nat.div_pos (by omega) hb
      omega
    have h1 := Nat.pow_log_le_self 2 hne
    have h2 := Nat.lt_pow_succ_log_self (by norm_num : 1 < 2) ((n - 1) / b)
    have h3 : b * ((n - 1) / b) ≤ n - 1 := Nat.mul_div_le _ _
    have h4 : b * 2 ^ Nat.log 2 ((n - 1) / b) ≤ b * ((n - 1) / b) := Nat.mul_le_mul_left b h1
    have h5 : n - 1 < 2 ^ (Nat.log 2 ((n - 1) / b)).succ * b := (Nat.div_lt_iff_lt_mul hb).mp h2
    refine ⟨h4.trans h3, ?_⟩
    calc n - 1 < 2 ^ (Nat.log 2 ((n - 1) / b)).succ * b := h5
      _ = 2 * (b * 2 ^ Nat.log 2 ((n - 1) / b)) := by rw [pow_succ]; ring
  have hinj0 : ∀ b b' j j' : ℕ, ¬ 2 ∣ b → j ≤ j' → b * 2 ^ j = b' * 2 ^ j' → b = b' := by
    intro b b' j j' hb hjj h
    obtain ⟨d, rfl⟩ := Nat.exists_eq_add_of_le hjj
    have h1 : b * 2 ^ j = (b' * 2 ^ d) * 2 ^ j := by rw [h, pow_add]; ring
    have h2 : b = b' * 2 ^ d := Nat.eq_of_mul_eq_mul_right (by positivity) h1
    rcases Nat.eq_zero_or_pos d with hd | hd
    · rw [hd] at h2; simpa using h2
    · exfalso; apply hb; rw [h2]
      exact Dvd.dvd.mul_left (dvd_pow_self 2 (by omega)) _
  have hinj : ∀ b b' j j' : ℕ, ¬ 2 ∣ b → ¬ 2 ∣ b' → b * 2 ^ j = b' * 2 ^ j' → b = b' := by
    intro b b' j j' hb hb' h
    rcases le_total j j' with hjj | hjj
    · exact hinj0 b b' j j' hb hjj h
    · exact (hinj0 b' b j' j hb' hjj h.symm).symm
  -- coprimality of t with (t·m − 1)
  have hcop : ∀ t m w : ℕ, w + 1 = t * m → Nat.Coprime w t := by
    intro t m w h
    have h1 : Nat.Coprime w (w + 1) := by simp
    rw [h] at h1
    exact Nat.Coprime.coprime_mul_right_right h1
  set φ : ℕ → ℕ := fun b => b * 2 ^ Nat.log 2 ((n - 1) / b) with hφdef
  set g : ℕ → ℕ := fun b =>
    if 2 ∣ b then b / 2 else if b = 2 * p + 1 then 2 * p - 1
    else if 2 * (φ b - 1) < n then 0 else φ b - 1 with hgdef
  have hmaps : ∀ b ∈ T, g b ∈ insert 0 (((Finset.Ioo 0 n).erase p).erase (2 * p)) := by
    intro b hb
    have hb0 := h0 b hb
    have hpb := hpT b hb
    rw [Finset.mem_insert, Finset.mem_erase, Finset.mem_erase, Finset.mem_Ioo]
    simp only [hgdef]
    by_cases h2 : 2 ∣ b
    · rw [if_pos h2]
      right
      obtain ⟨c, rfl⟩ := h2
      have := he _ hb ⟨c, rfl⟩
      rw [Nat.mul_div_cancel_left c (by norm_num : 0 < 2)]
      refine ⟨?_, ?_, ?_, ?_⟩
      · rintro rfl; exact hpb ⟨4, by ring⟩
      · rintro rfl; exact hpb ⟨2, by ring⟩
      · omega
      · omega
    · rw [if_neg h2]
      by_cases h3 : b = 2 * p + 1
      · rw [if_pos h3]; right; omega
      · rw [if_neg h3]
        by_cases h4 : 2 * (φ b - 1) < n
        · rw [if_pos h4]; left; rfl
        · rw [if_neg h4]
          right
          have hb1 := hφ b hb0 (ho b hb h2)
          have hne : φ b ≠ 2 * p + 1 := by
            intro h
            have h5 : b * 2 ^ Nat.log 2 ((n - 1) / b) = (2 * p + 1) * 2 ^ 0 := by simpa using h
            exact h3 (hinj _ _ _ _ h2 (by omega) h5)
          change φ b ≤ n - 1 ∧ n - 1 < 2 * φ b at hb1
          omega
  have hginj : Set.InjOn g (T : Set ℕ) := by
    -- even / odd collision is impossible
    have hEO : ∀ b ∈ T, ∀ t ∈ T, 2 ∣ b → ¬ 2 ∣ t → g b = g t → False := by
      intro b hb t ht h2b h2t h
      have hb0 := h0 b hb
      have ht0 := h0 t ht
      have hx' := hx b hb t ht h2b h2t
      obtain ⟨c, rfl⟩ := h2b
      simp only [hgdef] at h
      rw [if_pos ⟨c, rfl⟩, if_neg h2t, Nat.mul_div_cancel_left c (by norm_num : 0 < 2)] at h
      by_cases h3 : t = 2 * p + 1
      · rw [if_pos h3] at h
        have hc : Nat.Coprime c t := by
          have h1 : Nat.Coprime c (2 + c) := by
            rw [Nat.coprime_add_self_right]
            rw [Nat.coprime_comm, Nat.Prime.coprime_iff_not_dvd Nat.prime_two]
            intro hd; omega
          have : 2 + c = t := by omega
          rwa [this] at h1
        have h2t' : Nat.Coprime 2 t := (Nat.Prime.coprime_iff_not_dvd Nat.prime_two).mpr h2t
        have hg : (2 * c).gcd t = 1 := Nat.Coprime.mul_left h2t' hc
        rw [hg] at hx'
        omega
      · rw [if_neg h3] at h
        by_cases h4 : 2 * (φ t - 1) < n
        · rw [if_pos h4] at h; omega
        · rw [if_neg h4] at h
          have ht1 := hφ t ht0 (ho t ht h2t)
          change φ t ≤ n - 1 ∧ n - 1 < 2 * φ t at ht1
          have hc : Nat.Coprime c t := hcop t (2 ^ Nat.log 2 ((n - 1) / t)) c (by
            change c + 1 = φ t
            omega)
          have h2t' : Nat.Coprime 2 t := (Nat.Prime.coprime_iff_not_dvd Nat.prime_two).mpr h2t
          have hg : (2 * c).gcd t = 1 := Nat.Coprime.mul_left h2t' hc
          rw [hg] at hx'
          omega
    intro b hb b' hb' h
    have hb0 := h0 b hb
    have hb0' := h0 b' hb'
    by_cases h2 : 2 ∣ b
    · by_cases h2' : 2 ∣ b'
      · simp only [hgdef] at h
        rw [if_pos h2, if_pos h2'] at h
        obtain ⟨c, rfl⟩ := h2
        obtain ⟨c', rfl⟩ := h2'
        rw [Nat.mul_div_cancel_left c (by norm_num : 0 < 2),
          Nat.mul_div_cancel_left c' (by norm_num : 0 < 2)] at h
        rw [h]
      · exact (hEO b hb b' hb' h2 h2' h).elim
    · by_cases h2' : 2 ∣ b'
      · exact (hEO b' hb' b hb h2' h2 h.symm).elim
      · -- both odd
        have hb1 := hφ b hb0 (ho b hb h2)
        have hb1' := hφ b' hb0' (ho b' hb' h2')
        change φ b ≤ n - 1 ∧ n - 1 < 2 * φ b at hb1
        change φ b' ≤ n - 1 ∧ n - 1 < 2 * φ b' at hb1'
        have hφinj : φ b = φ b' → b = b' := fun e => hinj _ _ _ _ h2 h2' e
        have h2p' : ∀ t ∈ T, ¬ 2 ∣ t → φ t ≠ 2 * p := by
          intro t ht h2t e
          have hd : p ∣ t * 2 ^ Nat.log 2 ((n - 1) / t) := ⟨2, by change φ t = p * 2; omega⟩
          rcases (Nat.Prime.dvd_mul hp).mp hd with h5 | h5
          · exact hpT t ht h5
          · have h6 := Nat.Prime.dvd_of_dvd_pow hp h5
            have h7 := Nat.le_of_dvd (by norm_num) h6
            omega
        have e1 := h2p' b hb h2
        have e2 := h2p' b' hb' h2'
        simp only [hgdef] at h
        rw [if_neg h2, if_neg h2'] at h
        by_cases h3 : b = 2 * p + 1 <;> by_cases h3' : b' = 2 * p + 1
        · rw [h3, h3']
        · rw [if_pos h3, if_neg h3'] at h
          by_cases h4 : 2 * (φ b' - 1) < n
          · rw [if_pos h4] at h; omega
          · rw [if_neg h4] at h; omega
        · rw [if_neg h3, if_pos h3'] at h
          by_cases h4 : 2 * (φ b - 1) < n
          · rw [if_pos h4] at h; omega
          · rw [if_neg h4] at h; omega
        · rw [if_neg h3, if_neg h3'] at h
          by_cases h4 : 2 * (φ b - 1) < n <;> by_cases h4' : 2 * (φ b' - 1) < n
          · exact hφinj (by omega)
          · rw [if_pos h4, if_neg h4'] at h; omega
          · rw [if_neg h4, if_pos h4'] at h; omega
          · rw [if_neg h4, if_neg h4'] at h; exact hφinj (by omega)
  have hcard : (insert 0 (((Finset.Ioo 0 n).erase p).erase (2 * p))).card = n - 2 := by
    rw [Finset.card_insert_of_notMem (by simp), Finset.card_erase_of_mem, Finset.card_erase_of_mem,
      Nat.card_Ioo]
    · omega
    · rw [Finset.mem_Ioo]; omega
    · rw [Finset.mem_erase, Finset.mem_Ioo]; omega
  have hle := Finset.card_le_card_of_injOn g hmaps hginj
  rw [hcard] at hle
  omega
