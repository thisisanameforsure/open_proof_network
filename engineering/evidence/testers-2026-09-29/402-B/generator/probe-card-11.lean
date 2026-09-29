import Mathlib

theorem card_n_probe :
    ∀ (A : Finset ℕ), 0 ∉ A → A.card = 11 → ∃ a ∈ A, ∃ b ∈ A, a.gcd b ≤ (a / A.card : ℚ) := by
  intro A h0 hcard
  -- the rational inequality is 11 * gcd a b ≤ a
  have red : ∀ a b : ℕ, 11 * a.gcd b ≤ a → (a.gcd b : ℚ) ≤ (a / A.card : ℚ) := by
    intro a b h
    rw [hcard, le_div_iff₀ (by norm_num)]
    exact_mod_cast (by omega : a.gcd b * 11 ≤ a)
  have hne : A.Nonempty := Finset.card_pos.mp (by omega)
  obtain ⟨M, hMA, hMmax⟩ : ∃ M ∈ A, ∀ x ∈ A, x ≤ M :=
    ⟨A.max' hne, A.max'_mem hne, fun x hx => A.le_max' x hx⟩
  have hMpos : 0 < M := Nat.pos_of_ne_zero (by rintro rfl; exact h0 hMA)
  by_cases hsmall : ∃ x ∈ A, 11 * M.gcd x ≤ M
  · obtain ⟨x, hx, h⟩ := hsmall
    exact ⟨M, hMA, x, hx, red M x h⟩
  push Not at hsmall
  -- every other element x has 2520 * x = v * M for one of the 31 values v = 2520 * j / k
  have hval : ∀ x ∈ A.erase M, ∃ v ∈ ({252, 280, 315, 360, 420, 504, 560, 630, 720, 756, 840, 945, 1008, 1080, 1120, 1260, 1400, 1440, 1512, 1575, 1680, 1764, 1800, 1890, 1960, 2016, 2100, 2160, 2205, 2240, 2268} : Finset ℕ), 2520 * x = v * M := by
    intro x hx
    obtain ⟨hxM, hxA⟩ := Finset.mem_erase.mp hx
    have hxpos : 0 < x := Nat.pos_of_ne_zero (by rintro rfl; exact h0 hxA)
    have hlt : x < M := lt_of_le_of_ne (hMmax x hxA) hxM
    have hbig : M < 11 * M.gcd x := hsmall x hxA
    obtain ⟨k, hk⟩ := Nat.gcd_dvd_left M x
    obtain ⟨j, hj⟩ := Nat.gcd_dvd_right M x
    have hkN : k < 11 := by
      by_contra hh
      have : M.gcd x * 11 ≤ M.gcd x * k := Nat.mul_le_mul_left _ (by omega)
      omega
    have hjk : j < k := by
      have : M.gcd x * j < M.gcd x * k := by omega
      exact Nat.lt_of_mul_lt_mul_left this
    have hj0 : 0 < j := by
      rcases Nat.eq_zero_or_pos j with h | h
      · rw [h, Nat.mul_zero] at hj; omega
      · exact h
    refine ⟨2520 * j / k, ?_, ?_⟩
    · interval_cases k <;> interval_cases j <;> decide +kernel
    · interval_cases k <;> interval_cases j <;> omega
  -- colour the 31 values with 9 colours, each colour class pairwise good
  have hcol : ∀ v ∈ ({252, 280, 315, 360, 420, 504, 560, 630, 720, 756, 840, 945, 1008, 1080, 1120, 1260, 1400, 1440, 1512, 1575, 1680, 1764, 1800, 1890, 1960, 2016, 2100, 2160, 2205, 2240, 2268} : Finset ℕ), (fun a : ℕ => if a = 252 then 2 else if a = 280 then 6 else if a = 315 then 8 else if a = 360 then 7 else if a = 420 then 5 else if a = 504 then 4 else if a = 560 then 7 else if a = 630 then 3 else if a = 720 then 6 else if a = 756 then 6 else if a = 840 then 1 else if a = 945 then 2 else if a = 1008 then 5 else if a = 1080 then 5 else if a = 1120 then 3 else if a = 1260 then 0 else if a = 1400 then 4 else if a = 1440 then 4 else if a = 1512 then 3 else if a = 1575 then 1 else if a = 1680 then 2 else if a = 1764 then 7 else if a = 1800 then 2 else if a = 1890 then 4 else if a = 1960 then 0 else if a = 2016 then 1 else if a = 2100 then 6 else if a = 2160 then 0 else if a = 2205 then 5 else if a = 2240 then 5 else if a = 2268 then 8 else 0) v < 9 := by decide +kernel
  have hgood : ∀ v ∈ ({252, 280, 315, 360, 420, 504, 560, 630, 720, 756, 840, 945, 1008, 1080, 1120, 1260, 1400, 1440, 1512, 1575, 1680, 1764, 1800, 1890, 1960, 2016, 2100, 2160, 2205, 2240, 2268} : Finset ℕ), ∀ w ∈ ({252, 280, 315, 360, 420, 504, 560, 630, 720, 756, 840, 945, 1008, 1080, 1120, 1260, 1400, 1440, 1512, 1575, 1680, 1764, 1800, 1890, 1960, 2016, 2100, 2160, 2205, 2240, 2268} : Finset ℕ), v ≠ w → (fun a : ℕ => if a = 252 then 2 else if a = 280 then 6 else if a = 315 then 8 else if a = 360 then 7 else if a = 420 then 5 else if a = 504 then 4 else if a = 560 then 7 else if a = 630 then 3 else if a = 720 then 6 else if a = 756 then 6 else if a = 840 then 1 else if a = 945 then 2 else if a = 1008 then 5 else if a = 1080 then 5 else if a = 1120 then 3 else if a = 1260 then 0 else if a = 1400 then 4 else if a = 1440 then 4 else if a = 1512 then 3 else if a = 1575 then 1 else if a = 1680 then 2 else if a = 1764 then 7 else if a = 1800 then 2 else if a = 1890 then 4 else if a = 1960 then 0 else if a = 2016 then 1 else if a = 2100 then 6 else if a = 2160 then 0 else if a = 2205 then 5 else if a = 2240 then 5 else if a = 2268 then 8 else 0) v = (fun a : ℕ => if a = 252 then 2 else if a = 280 then 6 else if a = 315 then 8 else if a = 360 then 7 else if a = 420 then 5 else if a = 504 then 4 else if a = 560 then 7 else if a = 630 then 3 else if a = 720 then 6 else if a = 756 then 6 else if a = 840 then 1 else if a = 945 then 2 else if a = 1008 then 5 else if a = 1080 then 5 else if a = 1120 then 3 else if a = 1260 then 0 else if a = 1400 then 4 else if a = 1440 then 4 else if a = 1512 then 3 else if a = 1575 then 1 else if a = 1680 then 2 else if a = 1764 then 7 else if a = 1800 then 2 else if a = 1890 then 4 else if a = 1960 then 0 else if a = 2016 then 1 else if a = 2100 then 6 else if a = 2160 then 0 else if a = 2205 then 5 else if a = 2240 then 5 else if a = 2268 then 8 else 0) w →
      11 * v.gcd w ≤ v ∨ 11 * v.gcd w ≤ w := by decide +kernel
  have hmaps : ∀ x ∈ A.erase M, (fun a : ℕ => if a = 252 then 2 else if a = 280 then 6 else if a = 315 then 8 else if a = 360 then 7 else if a = 420 then 5 else if a = 504 then 4 else if a = 560 then 7 else if a = 630 then 3 else if a = 720 then 6 else if a = 756 then 6 else if a = 840 then 1 else if a = 945 then 2 else if a = 1008 then 5 else if a = 1080 then 5 else if a = 1120 then 3 else if a = 1260 then 0 else if a = 1400 then 4 else if a = 1440 then 4 else if a = 1512 then 3 else if a = 1575 then 1 else if a = 1680 then 2 else if a = 1764 then 7 else if a = 1800 then 2 else if a = 1890 then 4 else if a = 1960 then 0 else if a = 2016 then 1 else if a = 2100 then 6 else if a = 2160 then 0 else if a = 2205 then 5 else if a = 2240 then 5 else if a = 2268 then 8 else 0) (2520 * x / M) ∈ Finset.range 9 := by
    intro x hx
    obtain ⟨v, hv, hxv⟩ := hval x hx
    rw [Finset.mem_range, hxv, Nat.mul_div_cancel _ hMpos]
    exact hcol v hv
  have hcardE : (A.erase M).card = 10 := by rw [Finset.card_erase_of_mem hMA, hcard]
  obtain ⟨x, hx, y, hy, hxy, hc⟩ :=
    Finset.exists_ne_map_eq_of_card_lt_of_maps_to (by rw [hcardE, Finset.card_range]; omega) hmaps
  obtain ⟨v, hv, hxv⟩ := hval x hx
  obtain ⟨w, hw, hyw⟩ := hval y hy
  rw [hxv, hyw, Nat.mul_div_cancel _ hMpos, Nat.mul_div_cancel _ hMpos] at hc
  have hvw : v ≠ w := by
    rintro rfl
    exact hxy (by omega)
  have hg : v.gcd w * M = 2520 * x.gcd y := by
    rw [← Nat.gcd_mul_right, ← hxv, ← hyw, Nat.gcd_mul_left]
  have hxA := (Finset.mem_erase.mp hx).2
  have hyA := (Finset.mem_erase.mp hy).2
  rcases hgood v hv w hw hvw hc with h | h
  · have h2 : 11 * (v.gcd w * M) ≤ v * M := by
      rw [← Nat.mul_assoc]; exact Nat.mul_le_mul_right M h
    exact ⟨x, hxA, y, hyA, red x y (by omega)⟩
  · have h2 : 11 * (v.gcd w * M) ≤ w * M := by
      rw [← Nat.mul_assoc]; exact Nat.mul_le_mul_right M h
    exact ⟨y, hyA, x, hxA, red y x (by rw [Nat.gcd_comm]; omega)⟩
