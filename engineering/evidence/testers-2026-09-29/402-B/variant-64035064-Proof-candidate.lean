import Mathlib
import Nodes.«variant-64035064».Context

/-! Graham's gcd conjecture (Erdős problem 402) for sixteen-element sets. With M the largest
element, if gcd(M, x) > M/16 for every x then every other x is (j/k)M with j < k ≤ 15, so
L·x/M (L = lcm(1..15) = 360360) lies in a fixed set S of 71 values. S splits into 14 classes in
each of which any two distinct values c, d have 16·gcd(c, d) ≤ c or ≤ d; by pigeonhole two of
the 15 other elements share a class, and gcd(x, y)·L = gcd(c, d)·M transfers the bound. -/

theorem Opn.erdos_402_card_sixteen :
    ∀ (A : Finset ℕ), 0 ∉ A → A.card = 16 → ∃ a ∈ A, ∃ b ∈ A, a.gcd b ≤ (a / A.card : ℚ) := by
  intro A h0 hcard
  -- the rational inequality is 16 * gcd a b ≤ a
  have red : ∀ a b : ℕ, 16 * a.gcd b ≤ a → (a.gcd b : ℚ) ≤ (a / A.card : ℚ) := by
    intro a b h
    rw [hcard, le_div_iff₀ (by norm_num)]
    exact_mod_cast (by omega : a.gcd b * 16 ≤ a)
  have hne : A.Nonempty := Finset.card_pos.mp (by omega)
  obtain ⟨M, hMA, hMmax⟩ : ∃ M ∈ A, ∀ x ∈ A, x ≤ M :=
    ⟨A.max' hne, A.max'_mem hne, fun x hx => A.le_max' x hx⟩
  have hMpos : 0 < M := Nat.pos_of_ne_zero (by rintro rfl; exact h0 hMA)
  by_cases hsmall : ∃ x ∈ A, 16 * M.gcd x ≤ M
  · obtain ⟨x, hx, h⟩ := hsmall
    exact ⟨M, hMA, x, hx, red M x h⟩
  push Not at hsmall
  -- every other element x has 360360 * x = v * M for one of the 71 values v = 360360 * j / k
  have hval : ∀ x ∈ A.erase M, ∃ v ∈ ({24024, 25740, 27720, 30030, 32760, 36036, 40040, 45045, 48048, 51480, 55440, 60060, 65520, 72072, 77220, 80080, 83160, 90090, 96096, 98280, 102960, 108108, 110880, 120120, 128700, 131040, 135135, 138600, 144144, 150150, 154440, 160160, 163800, 166320, 168168, 180180, 192192, 194040, 196560, 200200, 205920, 210210, 216216, 221760, 225225, 229320, 231660, 240240, 249480, 252252, 257400, 262080, 264264, 270270, 277200, 280280, 283140, 288288, 294840, 300300, 304920, 308880, 312312, 315315, 320320, 324324, 327600, 330330, 332640, 334620, 336336} : Finset ℕ), 360360 * x = v * M := by
    intro x hx
    obtain ⟨hxM, hxA⟩ := Finset.mem_erase.mp hx
    have hxpos : 0 < x := Nat.pos_of_ne_zero (by rintro rfl; exact h0 hxA)
    have hlt : x < M := lt_of_le_of_ne (hMmax x hxA) hxM
    have hbig : M < 16 * M.gcd x := hsmall x hxA
    obtain ⟨k, hk⟩ := Nat.gcd_dvd_left M x
    obtain ⟨j, hj⟩ := Nat.gcd_dvd_right M x
    have hkN : k < 16 := by
      by_contra hh
      have : M.gcd x * 16 ≤ M.gcd x * k := Nat.mul_le_mul_left _ (by omega)
      omega
    have hjk : j < k := by
      have : M.gcd x * j < M.gcd x * k := by omega
      exact Nat.lt_of_mul_lt_mul_left this
    have hj0 : 0 < j := by
      rcases Nat.eq_zero_or_pos j with h | h
      · rw [h, Nat.mul_zero] at hj; omega
      · exact h
    refine ⟨360360 * j / k, ?_, ?_⟩
    · interval_cases k <;> interval_cases j <;> decide +kernel
    · interval_cases k <;> interval_cases j <;> omega
  -- colour the 71 values with 14 colours, each colour class pairwise good
  have hcol : ∀ v ∈ ({24024, 25740, 27720, 30030, 32760, 36036, 40040, 45045, 48048, 51480, 55440, 60060, 65520, 72072, 77220, 80080, 83160, 90090, 96096, 98280, 102960, 108108, 110880, 120120, 128700, 131040, 135135, 138600, 144144, 150150, 154440, 160160, 163800, 166320, 168168, 180180, 192192, 194040, 196560, 200200, 205920, 210210, 216216, 221760, 225225, 229320, 231660, 240240, 249480, 252252, 257400, 262080, 264264, 270270, 277200, 280280, 283140, 288288, 294840, 300300, 304920, 308880, 312312, 315315, 320320, 324324, 327600, 330330, 332640, 334620, 336336} : Finset ℕ), (fun a : ℕ => if a = 24024 then 9 else if a = 25740 then 11 else if a = 27720 then 12 else if a = 30030 then 6 else if a = 32760 then 8 else if a = 36036 then 2 else if a = 40040 then 10 else if a = 45045 then 13 else if a = 48048 then 8 else if a = 51480 then 7 else if a = 55440 then 10 else if a = 60060 then 5 else if a = 65520 then 12 else if a = 72072 then 3 else if a = 77220 then 6 else if a = 80080 then 11 else if a = 83160 then 2 else if a = 90090 then 4 else if a = 96096 then 4 else if a = 98280 then 11 else if a = 102960 then 9 else if a = 108108 then 10 else if a = 110880 then 8 else if a = 120120 then 1 else if a = 128700 then 2 else if a = 131040 then 5 else if a = 135135 then 9 else if a = 138600 then 5 else if a = 144144 then 6 else if a = 150150 then 3 else if a = 154440 then 8 else if a = 160160 then 3 else if a = 163800 then 6 else if a = 166320 then 3 else if a = 168168 then 11 else if a = 180180 then 0 else if a = 192192 then 0 else if a = 194040 then 6 else if a = 196560 then 4 else if a = 200200 then 7 else if a = 205920 then 10 else if a = 210210 then 8 else if a = 216216 then 5 else if a = 221760 then 4 else if a = 225225 then 10 else if a = 229320 then 3 else if a = 231660 then 3 else if a = 240240 then 2 else if a = 249480 then 1 else if a = 252252 then 1 else if a = 257400 then 4 else if a = 262080 then 1 else if a = 264264 then 10 else if a = 270270 then 7 else if a = 277200 then 7 else if a = 280280 then 4 else if a = 283140 then 12 else if a = 288288 then 7 else if a = 294840 then 2 else if a = 300300 then 9 else if a = 304920 then 9 else if a = 308880 then 1 else if a = 312312 then 13 else if a = 315315 then 2 else if a = 320320 then 5 else if a = 324324 then 4 else if a = 327600 then 0 else if a = 330330 then 11 else if a = 332640 then 0 else if a = 334620 then 5 else if a = 336336 then 12 else 0) v < 14 := by decide +kernel
  have hgood : ∀ v ∈ ({24024, 25740, 27720, 30030, 32760, 36036, 40040, 45045, 48048, 51480, 55440, 60060, 65520, 72072, 77220, 80080, 83160, 90090, 96096, 98280, 102960, 108108, 110880, 120120, 128700, 131040, 135135, 138600, 144144, 150150, 154440, 160160, 163800, 166320, 168168, 180180, 192192, 194040, 196560, 200200, 205920, 210210, 216216, 221760, 225225, 229320, 231660, 240240, 249480, 252252, 257400, 262080, 264264, 270270, 277200, 280280, 283140, 288288, 294840, 300300, 304920, 308880, 312312, 315315, 320320, 324324, 327600, 330330, 332640, 334620, 336336} : Finset ℕ), ∀ w ∈ ({24024, 25740, 27720, 30030, 32760, 36036, 40040, 45045, 48048, 51480, 55440, 60060, 65520, 72072, 77220, 80080, 83160, 90090, 96096, 98280, 102960, 108108, 110880, 120120, 128700, 131040, 135135, 138600, 144144, 150150, 154440, 160160, 163800, 166320, 168168, 180180, 192192, 194040, 196560, 200200, 205920, 210210, 216216, 221760, 225225, 229320, 231660, 240240, 249480, 252252, 257400, 262080, 264264, 270270, 277200, 280280, 283140, 288288, 294840, 300300, 304920, 308880, 312312, 315315, 320320, 324324, 327600, 330330, 332640, 334620, 336336} : Finset ℕ), v ≠ w → (fun a : ℕ => if a = 24024 then 9 else if a = 25740 then 11 else if a = 27720 then 12 else if a = 30030 then 6 else if a = 32760 then 8 else if a = 36036 then 2 else if a = 40040 then 10 else if a = 45045 then 13 else if a = 48048 then 8 else if a = 51480 then 7 else if a = 55440 then 10 else if a = 60060 then 5 else if a = 65520 then 12 else if a = 72072 then 3 else if a = 77220 then 6 else if a = 80080 then 11 else if a = 83160 then 2 else if a = 90090 then 4 else if a = 96096 then 4 else if a = 98280 then 11 else if a = 102960 then 9 else if a = 108108 then 10 else if a = 110880 then 8 else if a = 120120 then 1 else if a = 128700 then 2 else if a = 131040 then 5 else if a = 135135 then 9 else if a = 138600 then 5 else if a = 144144 then 6 else if a = 150150 then 3 else if a = 154440 then 8 else if a = 160160 then 3 else if a = 163800 then 6 else if a = 166320 then 3 else if a = 168168 then 11 else if a = 180180 then 0 else if a = 192192 then 0 else if a = 194040 then 6 else if a = 196560 then 4 else if a = 200200 then 7 else if a = 205920 then 10 else if a = 210210 then 8 else if a = 216216 then 5 else if a = 221760 then 4 else if a = 225225 then 10 else if a = 229320 then 3 else if a = 231660 then 3 else if a = 240240 then 2 else if a = 249480 then 1 else if a = 252252 then 1 else if a = 257400 then 4 else if a = 262080 then 1 else if a = 264264 then 10 else if a = 270270 then 7 else if a = 277200 then 7 else if a = 280280 then 4 else if a = 283140 then 12 else if a = 288288 then 7 else if a = 294840 then 2 else if a = 300300 then 9 else if a = 304920 then 9 else if a = 308880 then 1 else if a = 312312 then 13 else if a = 315315 then 2 else if a = 320320 then 5 else if a = 324324 then 4 else if a = 327600 then 0 else if a = 330330 then 11 else if a = 332640 then 0 else if a = 334620 then 5 else if a = 336336 then 12 else 0) v = (fun a : ℕ => if a = 24024 then 9 else if a = 25740 then 11 else if a = 27720 then 12 else if a = 30030 then 6 else if a = 32760 then 8 else if a = 36036 then 2 else if a = 40040 then 10 else if a = 45045 then 13 else if a = 48048 then 8 else if a = 51480 then 7 else if a = 55440 then 10 else if a = 60060 then 5 else if a = 65520 then 12 else if a = 72072 then 3 else if a = 77220 then 6 else if a = 80080 then 11 else if a = 83160 then 2 else if a = 90090 then 4 else if a = 96096 then 4 else if a = 98280 then 11 else if a = 102960 then 9 else if a = 108108 then 10 else if a = 110880 then 8 else if a = 120120 then 1 else if a = 128700 then 2 else if a = 131040 then 5 else if a = 135135 then 9 else if a = 138600 then 5 else if a = 144144 then 6 else if a = 150150 then 3 else if a = 154440 then 8 else if a = 160160 then 3 else if a = 163800 then 6 else if a = 166320 then 3 else if a = 168168 then 11 else if a = 180180 then 0 else if a = 192192 then 0 else if a = 194040 then 6 else if a = 196560 then 4 else if a = 200200 then 7 else if a = 205920 then 10 else if a = 210210 then 8 else if a = 216216 then 5 else if a = 221760 then 4 else if a = 225225 then 10 else if a = 229320 then 3 else if a = 231660 then 3 else if a = 240240 then 2 else if a = 249480 then 1 else if a = 252252 then 1 else if a = 257400 then 4 else if a = 262080 then 1 else if a = 264264 then 10 else if a = 270270 then 7 else if a = 277200 then 7 else if a = 280280 then 4 else if a = 283140 then 12 else if a = 288288 then 7 else if a = 294840 then 2 else if a = 300300 then 9 else if a = 304920 then 9 else if a = 308880 then 1 else if a = 312312 then 13 else if a = 315315 then 2 else if a = 320320 then 5 else if a = 324324 then 4 else if a = 327600 then 0 else if a = 330330 then 11 else if a = 332640 then 0 else if a = 334620 then 5 else if a = 336336 then 12 else 0) w →
      16 * v.gcd w ≤ v ∨ 16 * v.gcd w ≤ w := by decide +kernel
  have hmaps : ∀ x ∈ A.erase M, (fun a : ℕ => if a = 24024 then 9 else if a = 25740 then 11 else if a = 27720 then 12 else if a = 30030 then 6 else if a = 32760 then 8 else if a = 36036 then 2 else if a = 40040 then 10 else if a = 45045 then 13 else if a = 48048 then 8 else if a = 51480 then 7 else if a = 55440 then 10 else if a = 60060 then 5 else if a = 65520 then 12 else if a = 72072 then 3 else if a = 77220 then 6 else if a = 80080 then 11 else if a = 83160 then 2 else if a = 90090 then 4 else if a = 96096 then 4 else if a = 98280 then 11 else if a = 102960 then 9 else if a = 108108 then 10 else if a = 110880 then 8 else if a = 120120 then 1 else if a = 128700 then 2 else if a = 131040 then 5 else if a = 135135 then 9 else if a = 138600 then 5 else if a = 144144 then 6 else if a = 150150 then 3 else if a = 154440 then 8 else if a = 160160 then 3 else if a = 163800 then 6 else if a = 166320 then 3 else if a = 168168 then 11 else if a = 180180 then 0 else if a = 192192 then 0 else if a = 194040 then 6 else if a = 196560 then 4 else if a = 200200 then 7 else if a = 205920 then 10 else if a = 210210 then 8 else if a = 216216 then 5 else if a = 221760 then 4 else if a = 225225 then 10 else if a = 229320 then 3 else if a = 231660 then 3 else if a = 240240 then 2 else if a = 249480 then 1 else if a = 252252 then 1 else if a = 257400 then 4 else if a = 262080 then 1 else if a = 264264 then 10 else if a = 270270 then 7 else if a = 277200 then 7 else if a = 280280 then 4 else if a = 283140 then 12 else if a = 288288 then 7 else if a = 294840 then 2 else if a = 300300 then 9 else if a = 304920 then 9 else if a = 308880 then 1 else if a = 312312 then 13 else if a = 315315 then 2 else if a = 320320 then 5 else if a = 324324 then 4 else if a = 327600 then 0 else if a = 330330 then 11 else if a = 332640 then 0 else if a = 334620 then 5 else if a = 336336 then 12 else 0) (360360 * x / M) ∈ Finset.range 14 := by
    intro x hx
    obtain ⟨v, hv, hxv⟩ := hval x hx
    rw [Finset.mem_range, hxv, Nat.mul_div_cancel _ hMpos]
    exact hcol v hv
  have hcardE : (A.erase M).card = 15 := by rw [Finset.card_erase_of_mem hMA, hcard]
  obtain ⟨x, hx, y, hy, hxy, hc⟩ :=
    Finset.exists_ne_map_eq_of_card_lt_of_maps_to (by rw [hcardE, Finset.card_range]; omega) hmaps
  obtain ⟨v, hv, hxv⟩ := hval x hx
  obtain ⟨w, hw, hyw⟩ := hval y hy
  rw [hxv, hyw, Nat.mul_div_cancel _ hMpos, Nat.mul_div_cancel _ hMpos] at hc
  have hvw : v ≠ w := by
    rintro rfl
    exact hxy (by omega)
  have hg : v.gcd w * M = 360360 * x.gcd y := by
    rw [← Nat.gcd_mul_right, ← hxv, ← hyw, Nat.gcd_mul_left]
  have hxA := (Finset.mem_erase.mp hx).2
  have hyA := (Finset.mem_erase.mp hy).2
  rcases hgood v hv w hw hvw hc with h | h
  · have h2 : 16 * (v.gcd w * M) ≤ v * M := by
      rw [← Nat.mul_assoc]; exact Nat.mul_le_mul_right M h
    exact ⟨x, hxA, y, hyA, red x y (by omega)⟩
  · have h2 : 16 * (v.gcd w * M) ≤ w * M := by
      rw [← Nat.mul_assoc]; exact Nat.mul_le_mul_right M h
    exact ⟨y, hyA, x, hxA, red y x (by rw [Nat.gcd_comm]; omega)⟩
