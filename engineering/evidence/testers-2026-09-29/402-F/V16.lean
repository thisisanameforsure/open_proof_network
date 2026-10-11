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
  have red :
      ∀ (n L : ℕ) (S : Finset ℕ) (c : ℕ → ℕ), 2 ≤ n → 0 < L →
        (∀ k ∈ Finset.range n, ∀ j ∈ Finset.range k, 0 < j → k ∣ L * j ∧ L * j / k ∈ S) →
        (∀ a ∈ S, c a + 2 < n) →
        (∀ a ∈ S, ∀ b ∈ S, a ≠ b → c a = c b → n * a.gcd b ≤ a ∨ n * a.gcd b ≤ b) →
        ∀ A : Finset ℕ, 0 ∉ A → A.card = n → ∃ a ∈ A, ∃ b ∈ A, a.gcd b ≤ (a / A.card : ℚ) := by
    intro n L S c hn hL hS hc hgood A hA hcard
    have hpos : 0 < A.card := by omega
    have hne : A.Nonempty := Finset.card_pos.mp hpos
    have key : ∀ a b : ℕ, a.gcd b * A.card ≤ a → (a.gcd b : ℚ) ≤ (a / A.card : ℚ) := by
      intro a b h
      rw [le_div_iff₀ (by exact_mod_cast hpos)]
      exact_mod_cast h
    have hM : A.max' hne ∈ A := Finset.max'_mem A hne
    have hMpos : 0 < A.max' hne := Nat.pos_of_ne_zero (fun h => hA (h ▸ hM))
    by_cases hw : ∃ x ∈ A, (A.max' hne).gcd x * n ≤ A.max' hne
    · obtain ⟨x, hx, h⟩ := hw
      exact ⟨_, hM, x, hx, key _ x (by rw [hcard]; exact h)⟩
    push_neg at hw
    have forms : ∀ x ∈ A.erase (A.max' hne), ∃ a ∈ S, L * x = a * A.max' hne := by
      intro x hx
      rw [Finset.mem_erase] at hx
      obtain ⟨hxM, hxA⟩ := hx
      have hxpos : 0 < x := Nat.pos_of_ne_zero (fun h => hA (h ▸ hxA))
      have hlt : x < A.max' hne := lt_of_le_of_ne (Finset.le_max' A x hxA) hxM
      have hg := hw x hxA
      have hgpos : 0 < (A.max' hne).gcd x := Nat.gcd_pos_of_pos_right _ hxpos
      obtain ⟨k, hk⟩ := Nat.gcd_dvd_left (A.max' hne) x
      obtain ⟨j, hj⟩ := Nat.gcd_dvd_right (A.max' hne) x
      have hj1 : 0 < j := by
        rcases Nat.eq_zero_or_pos j with h | h
        · rw [h, Nat.mul_zero] at hj
          omega
        · exact h
      have hjk : j < k := by
        have h1 : (A.max' hne).gcd x * j < (A.max' hne).gcd x * k := by
          rw [← hj, ← hk]
          exact hlt
        exact Nat.lt_of_mul_lt_mul_left h1
      have hkn : k < n := by
        have h1 : (A.max' hne).gcd x * k < (A.max' hne).gcd x * n := by
          rw [← hk]
          exact hg
        exact Nat.lt_of_mul_lt_mul_left h1
      have hkx : k * x = j * A.max' hne := by
        calc k * x = k * ((A.max' hne).gcd x * j) := by rw [← hj]
          _ = j * ((A.max' hne).gcd x * k) := by ring
          _ = j * A.max' hne := by rw [← hk]
      have hkpos : 0 < k := by omega
      obtain ⟨hdvd, hmem⟩ := hS k (Finset.mem_range.2 hkn) j (Finset.mem_range.2 hjk) hj1
      obtain ⟨q, hq⟩ := hdvd
      refine ⟨L * j / k, hmem, ?_⟩
      rw [hq, Nat.mul_div_cancel_left q hkpos]
      apply Nat.eq_of_mul_eq_mul_left hkpos
      calc k * (L * x) = L * (k * x) := by ring
        _ = L * (j * A.max' hne) := by rw [hkx]
        _ = (L * j) * A.max' hne := by ring
        _ = (k * q) * A.max' hne := by rw [hq]
        _ = k * (q * A.max' hne) := by ring
    have hmaps : ∀ x ∈ A.erase (A.max' hne), c (L * x / A.max' hne) ∈ Finset.range (n - 2) := by
      intro x hx
      obtain ⟨a, ha, hax⟩ := forms x hx
      rw [Finset.mem_range, hax, Nat.mul_div_cancel _ hMpos]
      have := hc a ha
      omega
    have hcardE : (A.erase (A.max' hne)).card = n - 1 := by
      rw [Finset.card_erase_of_mem hM, hcard]
    obtain ⟨x, hx, y, hy, hxy, hcol⟩ :=
      Finset.exists_ne_map_eq_of_card_lt_of_maps_to
        (by rw [hcardE, Finset.card_range]; omega) hmaps
    obtain ⟨a, ha, hax⟩ := forms x hx
    obtain ⟨b, hb, hby⟩ := forms y hy
    rw [hax, hby, Nat.mul_div_cancel _ hMpos, Nat.mul_div_cancel _ hMpos] at hcol
    have hab : a ≠ b := by
      intro h
      apply hxy
      apply Nat.eq_of_mul_eq_mul_left hL
      rw [hax, hby, h]
    have hgcd : a.gcd b * A.max' hne = L * x.gcd y := by
      have h1 : Nat.gcd (L * x) (L * y) = L * x.gcd y := Nat.gcd_mul_left L x y
      rw [hax, hby, Nat.gcd_mul_right] at h1
      exact h1
    have hxA := (Finset.mem_erase.mp hx).2
    have hyA := (Finset.mem_erase.mp hy).2
    rcases hgood a ha b hb hab hcol with h | h
    · refine ⟨x, hxA, y, hyA, key x y ?_⟩
      rw [hcard]
      have h2 : L * (x.gcd y * n) ≤ L * x := by
        calc L * (x.gcd y * n) = n * (a.gcd b * A.max' hne) := by rw [hgcd]; ring
          _ ≤ a * A.max' hne := Nat.mul_le_mul_right _ h |>.trans_eq' (by ring)
          _ = L * x := hax.symm
      exact Nat.le_of_mul_le_mul_left h2 hL
    · refine ⟨y, hyA, x, hxA, key y x ?_⟩
      rw [hcard, Nat.gcd_comm]
      have h2 : L * (x.gcd y * n) ≤ L * y := by
        calc L * (x.gcd y * n) = n * (a.gcd b * A.max' hne) := by rw [hgcd]; ring
          _ ≤ b * A.max' hne := Nat.mul_le_mul_right _ h |>.trans_eq' (by ring)
          _ = L * y := hby.symm
      exact Nat.le_of_mul_le_mul_left h2 hL
  exact red 16 360360 {24024, 25740, 27720, 30030, 32760, 36036, 40040, 45045, 48048, 51480, 55440, 60060, 65520, 72072, 77220, 80080, 83160, 90090, 96096, 98280, 102960, 108108, 110880, 120120, 128700, 131040, 135135, 138600, 144144, 150150, 154440, 160160, 163800, 166320, 168168, 180180, 192192, 194040, 196560, 200200, 205920, 210210, 216216, 221760, 225225, 229320, 231660, 240240, 249480, 252252, 257400, 262080, 264264, 270270, 277200, 280280, 283140, 288288, 294840, 300300, 304920, 308880, 312312, 315315, 320320, 324324, 327600, 330330, 332640, 334620, 336336}
    (fun a : ℕ => if a = 24024 then 9 else if a = 25740 then 10 else if a = 27720 then 12 else if a = 30030 then 11 else if a = 32760 then 8 else if a = 36036 then 2 else if a = 40040 then 6 else if a = 45045 then 13 else if a = 48048 then 8 else if a = 51480 then 7 else if a = 55440 then 11 else if a = 60060 then 5 else if a = 65520 then 12 else if a = 72072 then 3 else if a = 77220 then 6 else if a = 80080 then 10 else if a = 83160 then 2 else if a = 90090 then 4 else if a = 96096 then 11 else if a = 98280 then 11 else if a = 102960 then 9 else if a = 108108 then 10 else if a = 110880 then 8 else if a = 120120 then 1 else if a = 128700 then 11 else if a = 131040 then 5 else if a = 135135 then 9 else if a = 138600 then 5 else if a = 144144 then 6 else if a = 150150 then 3 else if a = 154440 then 8 else if a = 160160 then 4 else if a = 163800 then 6 else if a = 166320 then 3 else if a = 168168 then 4 else if a = 180180 then 0 else if a = 192192 then 0 else if a = 194040 then 1 else if a = 196560 then 4 else if a = 200200 then 7 else if a = 205920 then 3 else if a = 210210 then 6 else if a = 216216 then 5 else if a = 221760 then 4 else if a = 225225 then 2 else if a = 229320 then 2 else if a = 231660 then 2 else if a = 240240 then 2 else if a = 249480 then 6 else if a = 252252 then 8 else if a = 257400 then 4 else if a = 262080 then 1 else if a = 264264 then 13 else if a = 270270 then 7 else if a = 277200 then 7 else if a = 280280 then 3 else if a = 283140 then 5 else if a = 288288 then 7 else if a = 294840 then 0 else if a = 300300 then 8 else if a = 304920 then 0 else if a = 308880 then 1 else if a = 312312 then 10 else if a = 315315 then 5 else if a = 320320 then 5 else if a = 324324 then 1 else if a = 327600 then 3 else if a = 330330 then 9 else if a = 332640 then 9 else if a = 334620 then 12 else if a = 336336 then 12 else 0)
    (by norm_num) (by norm_num) (by decide +kernel) (by decide +kernel) (by decide +kernel) A hA hn
