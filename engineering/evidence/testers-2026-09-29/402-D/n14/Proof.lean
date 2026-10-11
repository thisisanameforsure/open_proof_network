import Mathlib

/-! Graham's gcd conjecture (Erdős problem 402) restricted to sets of exactly fourteen positive
integers. Let M be the largest element. Either some x has gcd(M, x) ≤ M/14, or each other
element is (j/k)·M with 1 ≤ j < k ≤ 13, and multiplying by L = lcm(1..13) = 360360 and dividing
by M sends it to L·j/k, one of 57 fixed integers. Those 57 fall into 12 classes such that two
distinct members c, d of one class always have 14·gcd(c, d) ≤ c or 14·gcd(c, d) ≤ d. Thirteen
non-maximal elements in 12 classes put two, x and y, in one class, and gcd(x, y)·L = gcd(c, d)·M
carries the bound back to x and y. -/

theorem Opn.erdos_402_card_fourteen :
    ∀ (A : Finset ℕ), 0 ∉ A → A.card = 14 → ∃ a ∈ A, ∃ b ∈ A, a.gcd b ≤ (a / A.card : ℚ) := by
  intro A hA hn
  have hpos : 0 < A.card := by omega
  have hne : A.Nonempty := Finset.card_pos.mp hpos
  have key : ∀ a b : ℕ, a.gcd b * A.card ≤ a → (a.gcd b : ℚ) ≤ (a / A.card : ℚ) := by
    intro a b h
    rw [le_div_iff₀ (by exact_mod_cast hpos)]
    exact_mod_cast h
  have hM : A.max' hne ∈ A := Finset.max'_mem A hne
  have hMpos : 0 < A.max' hne := Nat.pos_of_ne_zero (fun h => hA (h ▸ hM))
  by_cases hw : ∃ x ∈ A, (A.max' hne).gcd x * 14 ≤ A.max' hne
  · obtain ⟨x, hx, h⟩ := hw
    exact ⟨_, hM, x, hx, key _ x (by rw [hn]; exact h)⟩
  push_neg at hw
  have hL : ∀ k < 14, 0 < k → 360360 / k * k = 360360 := by decide +kernel
  have H1 : ∀ k < 14, ∀ j < k, 0 < j →
      ([[32760, 102960, 110880, 270270, 320320], [90090, 163800, 194040, 288288], [30030, 138600, 144144, 154440, 196560, 280280], [180180, 229320, 332640], [36036, 55440, 150150, 262080], [27720, 65520, 200200, 205920, 216216, 330330], [51480, 80080, 108108, 131040, 166320, 300300], [60060, 225225, 249480, 252252, 327600], [45045, 83160, 240240, 257400], [40040, 98280, 210210, 221760, 324324], [120120, 277200, 308880, 315315], [72072, 135135, 160160, 294840, 304920]] : List (List ℕ)).findIdx (fun l => decide (360360 / k * j ∈ l)) < 12 ∧
      360360 / k * j ∈ ([[32760, 102960, 110880, 270270, 320320], [90090, 163800, 194040, 288288], [30030, 138600, 144144, 154440, 196560, 280280], [180180, 229320, 332640], [36036, 55440, 150150, 262080], [27720, 65520, 200200, 205920, 216216, 330330], [51480, 80080, 108108, 131040, 166320, 300300], [60060, 225225, 249480, 252252, 327600], [45045, 83160, 240240, 257400], [40040, 98280, 210210, 221760, 324324], [120120, 277200, 308880, 315315], [72072, 135135, 160160, 294840, 304920]] : List (List ℕ)).getD (([[32760, 102960, 110880, 270270, 320320], [90090, 163800, 194040, 288288], [30030, 138600, 144144, 154440, 196560, 280280], [180180, 229320, 332640], [36036, 55440, 150150, 262080], [27720, 65520, 200200, 205920, 216216, 330330], [51480, 80080, 108108, 131040, 166320, 300300], [60060, 225225, 249480, 252252, 327600], [45045, 83160, 240240, 257400], [40040, 98280, 210210, 221760, 324324], [120120, 277200, 308880, 315315], [72072, 135135, 160160, 294840, 304920]] : List (List ℕ)).findIdx (fun l => decide (360360 / k * j ∈ l))) [] := by
    decide +kernel
  have H2 : ∀ i < 12, ∀ v ∈ ([[32760, 102960, 110880, 270270, 320320], [90090, 163800, 194040, 288288], [30030, 138600, 144144, 154440, 196560, 280280], [180180, 229320, 332640], [36036, 55440, 150150, 262080], [27720, 65520, 200200, 205920, 216216, 330330], [51480, 80080, 108108, 131040, 166320, 300300], [60060, 225225, 249480, 252252, 327600], [45045, 83160, 240240, 257400], [40040, 98280, 210210, 221760, 324324], [120120, 277200, 308880, 315315], [72072, 135135, 160160, 294840, 304920]] : List (List ℕ)).getD i [], ∀ w ∈ ([[32760, 102960, 110880, 270270, 320320], [90090, 163800, 194040, 288288], [30030, 138600, 144144, 154440, 196560, 280280], [180180, 229320, 332640], [36036, 55440, 150150, 262080], [27720, 65520, 200200, 205920, 216216, 330330], [51480, 80080, 108108, 131040, 166320, 300300], [60060, 225225, 249480, 252252, 327600], [45045, 83160, 240240, 257400], [40040, 98280, 210210, 221760, 324324], [120120, 277200, 308880, 315315], [72072, 135135, 160160, 294840, 304920]] : List (List ℕ)).getD i [], v ≠ w →
      14 * v.gcd w ≤ v ∨ 14 * v.gcd w ≤ w := by
    decide +kernel
  have forms : ∀ x ∈ A.erase (A.max' hne), ∃ k j, k < 14 ∧ j < k ∧ 0 < j ∧
      360360 * x = 360360 / k * j * A.max' hne := by
    intro x hx
    rw [Finset.mem_erase] at hx
    have hxpos : 0 < x := Nat.pos_of_ne_zero (fun h => hA (h ▸ hx.2))
    have hlt : x < A.max' hne := lt_of_le_of_ne (Finset.le_max' A x hx.2) hx.1
    have hg := hw x hx.2
    obtain ⟨k, hk⟩ := Nat.gcd_dvd_left (A.max' hne) x
    obtain ⟨j, hj⟩ := Nat.gcd_dvd_right (A.max' hne) x
    have hgpos : 0 < (A.max' hne).gcd x := Nat.gcd_pos_of_pos_right _ hxpos
    have hkN : k < 14 := by
      by_contra hh
      push_neg at hh
      have := Nat.mul_le_mul_left ((A.max' hne).gcd x) hh
      omega
    have hjk : j < k := by
      by_contra hh
      push_neg at hh
      have := Nat.mul_le_mul_left ((A.max' hne).gcd x) hh
      omega
    have hj1 : 0 < j := by
      rcases Nat.eq_zero_or_pos j with h | h
      · subst h
        omega
      · exact h
    refine ⟨k, j, hkN, hjk, hj1, ?_⟩
    have hLk := hL k hkN (by omega)
    obtain ⟨g, hgd⟩ : ∃ g, (A.max' hne).gcd x = g := ⟨_, rfl⟩
    rw [hgd] at hk hj
    rw [hj, hk]
    calc 360360 * (g * j) = (360360 / k * k) * (g * j) := by rw [hLk]
      _ = 360360 / k * j * (g * k) := by ring
  have hcard : (A.erase (A.max' hne)).card = 13 := by
    rw [Finset.card_erase_of_mem hM, hn]
  have hmaps : ∀ x ∈ A.erase (A.max' hne),
      ([[32760, 102960, 110880, 270270, 320320], [90090, 163800, 194040, 288288], [30030, 138600, 144144, 154440, 196560, 280280], [180180, 229320, 332640], [36036, 55440, 150150, 262080], [27720, 65520, 200200, 205920, 216216, 330330], [51480, 80080, 108108, 131040, 166320, 300300], [60060, 225225, 249480, 252252, 327600], [45045, 83160, 240240, 257400], [40040, 98280, 210210, 221760, 324324], [120120, 277200, 308880, 315315], [72072, 135135, 160160, 294840, 304920]] : List (List ℕ)).findIdx (fun l => decide (360360 * x / A.max' hne ∈ l)) ∈ Finset.range 12 := by
    intro x hx
    obtain ⟨k, j, hk, hj, hj0, he⟩ := forms x hx
    rw [Finset.mem_range, he, Nat.mul_div_cancel _ hMpos]
    exact (H1 k hk j hj hj0).1
  obtain ⟨x, hx, y, hy, hxy, hc⟩ :=
    Finset.exists_ne_map_eq_of_card_lt_of_maps_to (by rw [hcard, Finset.card_range]; norm_num) hmaps
  obtain ⟨k, j, hk, hj, hj0, hex⟩ := forms x hx
  obtain ⟨k', j', hk', hj', hj0', hey⟩ := forms y hy
  have ex' : 360360 * x / A.max' hne = 360360 / k * j := by
    rw [hex, Nat.mul_div_cancel _ hMpos]
  have ey' : 360360 * y / A.max' hne = 360360 / k' * j' := by
    rw [hey, Nat.mul_div_cancel _ hMpos]
  simp only [ex', ey'] at hc
  have h1 := (H1 k hk j hj hj0).2
  have h2 := (H1 k' hk' j' hj' hj0').2
  rw [hc] at h1
  have hvw : 360360 / k * j ≠ 360360 / k' * j' := by
    intro h
    apply hxy
    rw [h] at hex
    omega
  have hgcd : (360360 / k * j).gcd (360360 / k' * j') * A.max' hne = 360360 * x.gcd y := by
    have h := Nat.gcd_mul_left 360360 x y
    rw [hex, hey, Nat.gcd_mul_right] at h
    exact h
  have hxA := (Finset.mem_erase.mp hx).2
  have hyA := (Finset.mem_erase.mp hy).2
  rcases H2 _ (H1 k' hk' j' hj' hj0').1 _ h1 _ h2 hvw with h | h
  · refine ⟨x, hxA, y, hyA, key x y ?_⟩
    rw [hn]
    have h3 := Nat.mul_le_mul_right (A.max' hne) h
    have h4 : x.gcd y * 14 * 360360 ≤ x * 360360 := by nlinarith
    exact Nat.le_of_mul_le_mul_right h4 (by norm_num)
  · refine ⟨y, hyA, x, hxA, key y x ?_⟩
    rw [hn, Nat.gcd_comm]
    have h3 := Nat.mul_le_mul_right (A.max' hne) h
    have h4 : x.gcd y * 14 * 360360 ≤ y * 360360 := by nlinarith
    exact Nat.le_of_mul_le_mul_right h4 (by norm_num)
