import Mathlib
import Nodes.«variant-64035064».Context

/-! Graham's gcd conjecture (Erdős problem 402) for sixteen-element sets. With M the largest
element, if gcd(M, x) > M/16 for every x then every other x is (j/k)M with j < k ≤ 15, so
L·x/M (L = lcm(1..15) = 360360) lies in a fixed set S of 71 values. S splits into 14 classes in
each of which any two distinct values c, d have 16·gcd(c, d) ≤ c or ≤ d; by pigeonhole two of
the 15 other elements share a class, and gcd(x, y)·L = gcd(c, d)·M transfers the bound. -/

theorem Opn.erdos_402_card_sixteen :
    ∀ (A : Finset ℕ), 0 ∉ A → A.card = 16 → ∃ a ∈ A, ∃ b ∈ A, a.gcd b ≤ (a / A.card : ℚ) := by
  intro A hA hn
  have hpos : 0 < A.card := by omega
  have hne : A.Nonempty := Finset.card_pos.mp hpos
  have key : ∀ a b : ℕ, a.gcd b * A.card ≤ a → (a.gcd b : ℚ) ≤ (a / A.card : ℚ) := by
    intro a b h
    rw [le_div_iff₀ (by exact_mod_cast hpos)]
    exact_mod_cast h
  have hM : A.max' hne ∈ A := Finset.max'_mem A hne
  have hMpos : 0 < A.max' hne := Nat.pos_of_ne_zero (fun h => hA (h ▸ hM))
  by_cases hw : ∃ x ∈ A, (A.max' hne).gcd x * 16 ≤ A.max' hne
  · obtain ⟨x, hx, h⟩ := hw
    exact ⟨_, hM, x, hx, key _ x (by rw [hn]; exact h)⟩
  push_neg at hw
  have forms : ∀ x ∈ A.erase (A.max' hne), ∃ a ∈ ({24024, 25740, 27720, 30030, 32760, 36036, 40040, 45045, 48048, 51480, 55440, 60060, 65520, 72072, 77220, 80080, 83160, 90090, 96096, 98280, 102960, 108108, 110880, 120120, 128700, 131040, 135135, 138600, 144144, 150150, 154440, 160160, 163800, 166320, 168168, 180180, 192192, 194040, 196560, 200200, 205920, 210210, 216216, 221760, 225225, 229320, 231660, 240240, 249480, 252252, 257400, 262080, 264264, 270270, 277200, 280280, 283140, 288288, 294840, 300300, 304920, 308880, 312312, 315315, 320320, 324324, 327600, 330330, 332640, 334620, 336336} : Finset ℕ), 360360 * x = a * A.max' hne := by
    intro x hx
    rw [Finset.mem_erase] at hx
    have hxpos : 0 < x := Nat.pos_of_ne_zero (fun h => hA (h ▸ hx.2))
    have hlt : x < A.max' hne := lt_of_le_of_ne (Finset.le_max' A x hx.2) hx.1
    have hg := hw x hx.2
    obtain ⟨k, hk⟩ := Nat.gcd_dvd_left (A.max' hne) x
    obtain ⟨j, hj⟩ := Nat.gcd_dvd_right (A.max' hne) x
    have hgpos : 0 < (A.max' hne).gcd x := Nat.gcd_pos_of_pos_right _ hxpos
    have hkN : k < 16 := by
      by_contra hh
      push_neg at hh
      have := Nat.mul_le_mul_left ((A.max' hne).gcd x) hh
      omega
    have hjk : j < k := by
      by_contra hh
      push_neg at hh
      have := Nat.mul_le_mul_left ((A.max' hne).gcd x) hh
      omega
    have hj1 : 1 ≤ j := by
      rcases Nat.eq_zero_or_pos j with h | h
      · subst h
        omega
      · exact h
    have hk0 : 0 < k := by omega
    have hmemall : ∀ k < 16, ∀ j < k, 1 ≤ j → 360360 * j / k ∈ ({24024, 25740, 27720, 30030, 32760, 36036, 40040, 45045, 48048, 51480, 55440, 60060, 65520, 72072, 77220, 80080, 83160, 90090, 96096, 98280, 102960, 108108, 110880, 120120, 128700, 131040, 135135, 138600, 144144, 150150, 154440, 160160, 163800, 166320, 168168, 180180, 192192, 194040, 196560, 200200, 205920, 210210, 216216, 221760, 225225, 229320, 231660, 240240, 249480, 252252, 257400, 262080, 264264, 270270, 277200, 280280, 283140, 288288, 294840, 300300, 304920, 308880, 312312, 315315, 320320, 324324, 327600, 330330, 332640, 334620, 336336} : Finset ℕ) := by decide +kernel
    have hdvdall : ∀ k < 16, 0 < k → k ∣ 360360 := by decide +kernel
    refine ⟨360360 * j / k, hmemall k hkN j hjk hj1, ?_⟩
    obtain ⟨q, hq⟩ := hdvdall k hkN hk0
    have hdiv : 360360 * j / k = q * j := by
      rw [hq, Nat.mul_assoc, Nat.mul_div_cancel_left _ hk0]
    rw [hdiv, hq]
    conv_lhs => rw [hj]
    conv_rhs => rw [hk]
    ring
  have hcard : (A.erase (A.max' hne)).card = 15 := by
    rw [Finset.card_erase_of_mem hM, hn]
  have hS : ∀ a ∈ ({24024, 25740, 27720, 30030, 32760, 36036, 40040, 45045, 48048, 51480, 55440, 60060, 65520, 72072, 77220, 80080, 83160, 90090, 96096, 98280, 102960, 108108, 110880, 120120, 128700, 131040, 135135, 138600, 144144, 150150, 154440, 160160, 163800, 166320, 168168, 180180, 192192, 194040, 196560, 200200, 205920, 210210, 216216, 221760, 225225, 229320, 231660, 240240, 249480, 252252, 257400, 262080, 264264, 270270, 277200, 280280, 283140, 288288, 294840, 300300, 304920, 308880, 312312, 315315, 320320, 324324, 327600, 330330, 332640, 334620, 336336} : Finset ℕ), (fun a : ℕ => if a = 24024 then 8 else if a = 25740 then 10 else if a = 27720 then 6 else if a = 30030 then 11 else if a = 32760 then 9 else if a = 36036 then 2 else if a = 40040 then 12 else if a = 45045 then 13 else if a = 48048 then 9 else if a = 51480 then 7 else if a = 55440 then 10 else if a = 60060 then 5 else if a = 65520 then 11 else if a = 72072 then 3 else if a = 77220 then 6 else if a = 80080 then 13 else if a = 83160 then 2 else if a = 90090 then 4 else if a = 96096 then 7 else if a = 98280 then 12 else if a = 102960 then 8 else if a = 108108 then 10 else if a = 110880 then 5 else if a = 120120 then 1 else if a = 128700 then 2 else if a = 131040 then 10 else if a = 135135 then 8 else if a = 138600 then 7 else if a = 144144 then 6 else if a = 150150 then 6 else if a = 154440 then 9 else if a = 160160 then 11 else if a = 163800 then 5 else if a = 166320 then 3 else if a = 168168 then 11 else if a = 180180 then 0 else if a = 192192 then 0 else if a = 194040 then 1 else if a = 196560 then 4 else if a = 200200 then 8 else if a = 205920 then 3 else if a = 210210 then 9 else if a = 216216 then 5 else if a = 221760 then 8 else if a = 225225 then 10 else if a = 229320 then 2 else if a = 231660 then 11 else if a = 240240 then 2 else if a = 249480 then 0 else if a = 252252 then 8 else if a = 257400 then 4 else if a = 262080 then 1 else if a = 264264 then 10 else if a = 270270 then 7 else if a = 277200 then 9 else if a = 280280 then 4 else if a = 283140 then 5 else if a = 288288 then 4 else if a = 294840 then 3 else if a = 300300 then 3 else if a = 304920 then 4 else if a = 308880 then 1 else if a = 312312 then 13 else if a = 315315 then 3 else if a = 320320 then 5 else if a = 324324 then 1 else if a = 327600 then 0 else if a = 330330 then 8 else if a = 332640 then 11 else if a = 334620 then 12 else if a = 336336 then 12 else 0) a < 14 := by decide +kernel
  have hmaps : ∀ x ∈ A.erase (A.max' hne), (fun a : ℕ => if a = 24024 then 8 else if a = 25740 then 10 else if a = 27720 then 6 else if a = 30030 then 11 else if a = 32760 then 9 else if a = 36036 then 2 else if a = 40040 then 12 else if a = 45045 then 13 else if a = 48048 then 9 else if a = 51480 then 7 else if a = 55440 then 10 else if a = 60060 then 5 else if a = 65520 then 11 else if a = 72072 then 3 else if a = 77220 then 6 else if a = 80080 then 13 else if a = 83160 then 2 else if a = 90090 then 4 else if a = 96096 then 7 else if a = 98280 then 12 else if a = 102960 then 8 else if a = 108108 then 10 else if a = 110880 then 5 else if a = 120120 then 1 else if a = 128700 then 2 else if a = 131040 then 10 else if a = 135135 then 8 else if a = 138600 then 7 else if a = 144144 then 6 else if a = 150150 then 6 else if a = 154440 then 9 else if a = 160160 then 11 else if a = 163800 then 5 else if a = 166320 then 3 else if a = 168168 then 11 else if a = 180180 then 0 else if a = 192192 then 0 else if a = 194040 then 1 else if a = 196560 then 4 else if a = 200200 then 8 else if a = 205920 then 3 else if a = 210210 then 9 else if a = 216216 then 5 else if a = 221760 then 8 else if a = 225225 then 10 else if a = 229320 then 2 else if a = 231660 then 11 else if a = 240240 then 2 else if a = 249480 then 0 else if a = 252252 then 8 else if a = 257400 then 4 else if a = 262080 then 1 else if a = 264264 then 10 else if a = 270270 then 7 else if a = 277200 then 9 else if a = 280280 then 4 else if a = 283140 then 5 else if a = 288288 then 4 else if a = 294840 then 3 else if a = 300300 then 3 else if a = 304920 then 4 else if a = 308880 then 1 else if a = 312312 then 13 else if a = 315315 then 3 else if a = 320320 then 5 else if a = 324324 then 1 else if a = 327600 then 0 else if a = 330330 then 8 else if a = 332640 then 11 else if a = 334620 then 12 else if a = 336336 then 12 else 0) (360360 * x / A.max' hne) ∈ Finset.range 14 := by
    intro x hx
    obtain ⟨a, ha, hax⟩ := forms x hx
    rw [Finset.mem_range, hax, Nat.mul_div_cancel _ hMpos]
    exact hS a ha
  obtain ⟨x, hx, y, hy, hxy, hc⟩ :=
    Finset.exists_ne_map_eq_of_card_lt_of_maps_to (by rw [hcard, Finset.card_range]; norm_num) hmaps
  obtain ⟨a, ha, hax⟩ := forms x hx
  obtain ⟨b, hb, hby⟩ := forms y hy
  rw [hax, hby, Nat.mul_div_cancel _ hMpos, Nat.mul_div_cancel _ hMpos] at hc
  have hab : a ≠ b := by
    intro h
    subst h
    apply hxy
    omega
  have hpair : ∀ a ∈ ({24024, 25740, 27720, 30030, 32760, 36036, 40040, 45045, 48048, 51480, 55440, 60060, 65520, 72072, 77220, 80080, 83160, 90090, 96096, 98280, 102960, 108108, 110880, 120120, 128700, 131040, 135135, 138600, 144144, 150150, 154440, 160160, 163800, 166320, 168168, 180180, 192192, 194040, 196560, 200200, 205920, 210210, 216216, 221760, 225225, 229320, 231660, 240240, 249480, 252252, 257400, 262080, 264264, 270270, 277200, 280280, 283140, 288288, 294840, 300300, 304920, 308880, 312312, 315315, 320320, 324324, 327600, 330330, 332640, 334620, 336336} : Finset ℕ), ∀ b ∈ ({24024, 25740, 27720, 30030, 32760, 36036, 40040, 45045, 48048, 51480, 55440, 60060, 65520, 72072, 77220, 80080, 83160, 90090, 96096, 98280, 102960, 108108, 110880, 120120, 128700, 131040, 135135, 138600, 144144, 150150, 154440, 160160, 163800, 166320, 168168, 180180, 192192, 194040, 196560, 200200, 205920, 210210, 216216, 221760, 225225, 229320, 231660, 240240, 249480, 252252, 257400, 262080, 264264, 270270, 277200, 280280, 283140, 288288, 294840, 300300, 304920, 308880, 312312, 315315, 320320, 324324, 327600, 330330, 332640, 334620, 336336} : Finset ℕ), a ≠ b → (fun a : ℕ => if a = 24024 then 8 else if a = 25740 then 10 else if a = 27720 then 6 else if a = 30030 then 11 else if a = 32760 then 9 else if a = 36036 then 2 else if a = 40040 then 12 else if a = 45045 then 13 else if a = 48048 then 9 else if a = 51480 then 7 else if a = 55440 then 10 else if a = 60060 then 5 else if a = 65520 then 11 else if a = 72072 then 3 else if a = 77220 then 6 else if a = 80080 then 13 else if a = 83160 then 2 else if a = 90090 then 4 else if a = 96096 then 7 else if a = 98280 then 12 else if a = 102960 then 8 else if a = 108108 then 10 else if a = 110880 then 5 else if a = 120120 then 1 else if a = 128700 then 2 else if a = 131040 then 10 else if a = 135135 then 8 else if a = 138600 then 7 else if a = 144144 then 6 else if a = 150150 then 6 else if a = 154440 then 9 else if a = 160160 then 11 else if a = 163800 then 5 else if a = 166320 then 3 else if a = 168168 then 11 else if a = 180180 then 0 else if a = 192192 then 0 else if a = 194040 then 1 else if a = 196560 then 4 else if a = 200200 then 8 else if a = 205920 then 3 else if a = 210210 then 9 else if a = 216216 then 5 else if a = 221760 then 8 else if a = 225225 then 10 else if a = 229320 then 2 else if a = 231660 then 11 else if a = 240240 then 2 else if a = 249480 then 0 else if a = 252252 then 8 else if a = 257400 then 4 else if a = 262080 then 1 else if a = 264264 then 10 else if a = 270270 then 7 else if a = 277200 then 9 else if a = 280280 then 4 else if a = 283140 then 5 else if a = 288288 then 4 else if a = 294840 then 3 else if a = 300300 then 3 else if a = 304920 then 4 else if a = 308880 then 1 else if a = 312312 then 13 else if a = 315315 then 3 else if a = 320320 then 5 else if a = 324324 then 1 else if a = 327600 then 0 else if a = 330330 then 8 else if a = 332640 then 11 else if a = 334620 then 12 else if a = 336336 then 12 else 0) a = (fun a : ℕ => if a = 24024 then 8 else if a = 25740 then 10 else if a = 27720 then 6 else if a = 30030 then 11 else if a = 32760 then 9 else if a = 36036 then 2 else if a = 40040 then 12 else if a = 45045 then 13 else if a = 48048 then 9 else if a = 51480 then 7 else if a = 55440 then 10 else if a = 60060 then 5 else if a = 65520 then 11 else if a = 72072 then 3 else if a = 77220 then 6 else if a = 80080 then 13 else if a = 83160 then 2 else if a = 90090 then 4 else if a = 96096 then 7 else if a = 98280 then 12 else if a = 102960 then 8 else if a = 108108 then 10 else if a = 110880 then 5 else if a = 120120 then 1 else if a = 128700 then 2 else if a = 131040 then 10 else if a = 135135 then 8 else if a = 138600 then 7 else if a = 144144 then 6 else if a = 150150 then 6 else if a = 154440 then 9 else if a = 160160 then 11 else if a = 163800 then 5 else if a = 166320 then 3 else if a = 168168 then 11 else if a = 180180 then 0 else if a = 192192 then 0 else if a = 194040 then 1 else if a = 196560 then 4 else if a = 200200 then 8 else if a = 205920 then 3 else if a = 210210 then 9 else if a = 216216 then 5 else if a = 221760 then 8 else if a = 225225 then 10 else if a = 229320 then 2 else if a = 231660 then 11 else if a = 240240 then 2 else if a = 249480 then 0 else if a = 252252 then 8 else if a = 257400 then 4 else if a = 262080 then 1 else if a = 264264 then 10 else if a = 270270 then 7 else if a = 277200 then 9 else if a = 280280 then 4 else if a = 283140 then 5 else if a = 288288 then 4 else if a = 294840 then 3 else if a = 300300 then 3 else if a = 304920 then 4 else if a = 308880 then 1 else if a = 312312 then 13 else if a = 315315 then 3 else if a = 320320 then 5 else if a = 324324 then 1 else if a = 327600 then 0 else if a = 330330 then 8 else if a = 332640 then 11 else if a = 334620 then 12 else if a = 336336 then 12 else 0) b →
      16 * a.gcd b ≤ a ∨ 16 * a.gcd b ≤ b := by decide +kernel
  have hgcd : a.gcd b * A.max' hne = 360360 * x.gcd y := by
    have h1 : Nat.gcd (360360 * x) (360360 * y) = 360360 * x.gcd y := Nat.gcd_mul_left 360360 x y
    rw [hax, hby, Nat.gcd_mul_right] at h1
    exact h1
  have hxA := (Finset.mem_erase.mp hx).2
  have hyA := (Finset.mem_erase.mp hy).2
  rcases hpair a ha b hb hab hc with h | h
  · refine ⟨x, hxA, y, hyA, key x y ?_⟩
    rw [hn]
    have h2 := Nat.mul_le_mul_right (A.max' hne) h
    have h3 : x.gcd y * 16 * 360360 ≤ x * 360360 := by nlinarith
    exact Nat.le_of_mul_le_mul_right h3 (by norm_num)
  · refine ⟨y, hyA, x, hxA, key y x ?_⟩
    rw [hn, Nat.gcd_comm]
    have h2 := Nat.mul_le_mul_right (A.max' hne) h
    have h3 : x.gcd y * 16 * 360360 ≤ y * 360360 := by nlinarith
    exact Nat.le_of_mul_le_mul_right h3 (by norm_num)
