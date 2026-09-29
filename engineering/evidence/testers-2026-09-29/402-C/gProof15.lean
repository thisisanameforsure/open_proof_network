import Mathlib

theorem Opn.erdos_402_card_fifteen :
    ∀ (A : Finset ℕ), 0 ∉ A → A.card = 15 → ∃ a ∈ A, ∃ b ∈ A, a.gcd b ≤ (a / A.card : ℚ) := by
  intro A hA hn
  have hpos : 0 < A.card := by omega
  have hne : A.Nonempty := Finset.card_pos.mp hpos
  have key : ∀ a b : ℕ, a.gcd b * A.card ≤ a → (a.gcd b : ℚ) ≤ (a / A.card : ℚ) := by
    intro a b h
    rw [le_div_iff₀ (by exact_mod_cast hpos)]
    exact_mod_cast h
  obtain ⟨M, hMdef⟩ : ∃ M, M = A.max' hne := ⟨_, rfl⟩
  have hM : M ∈ A := by rw [hMdef]; exact Finset.max'_mem A hne
  have hle : ∀ x ∈ A, x ≤ M := by
    intro x hx
    rw [hMdef]
    exact Finset.le_max' A x hx
  have hMpos : 0 < M := Nat.pos_of_ne_zero (fun h => hA (h ▸ hM))
  by_cases hw : ∃ x ∈ A, M.gcd x * 15 ≤ M
  · obtain ⟨x, hx, h⟩ := hw
    exact ⟨M, hM, x, hx, key M x (by rw [hn]; exact h)⟩
  push Not at hw
  obtain ⟨S, hS⟩ : ∃ S : List ℕ, S = [25740, 27720, 30030, 32760, 36036, 40040, 45045, 51480, 55440, 60060, 65520, 72072, 77220, 80080, 83160, 90090, 98280, 102960, 108108, 110880, 120120, 128700, 131040, 135135, 138600, 144144, 150150, 154440, 160160, 163800, 166320, 180180, 194040, 196560, 200200, 205920, 210210, 216216, 221760, 225225, 229320, 231660, 240240, 249480, 252252, 257400, 262080, 270270, 277200, 280280, 283140, 288288, 294840, 300300, 304920, 308880, 315315, 320320, 324324, 327600, 330330, 332640, 334620] := ⟨_, rfl⟩
  obtain ⟨C, hC⟩ : ∃ C : List (List ℕ), C = [[180180, 221760, 294840], [120120, 166320, 225225, 231660, 252252, 327600], [90090, 196560, 200200, 205920, 304920, 324324], [32760, 77220, 240240, 249480, 315315], [60060, 138600, 154440, 229320, 288288], [51480, 108108, 110880, 150150, 262080, 280280], [30030, 102960, 163800, 194040, 216216, 320320], [72072, 160160, 270270, 277200, 283140], [40040, 55440, 131040, 135135, 300300, 308880], [27720, 98280, 144144, 210210, 257400], [36036, 65520, 83160, 128700, 330330], [25740, 80080, 332640], [45045, 334620]] := ⟨_, rfl⟩
  have P1 : ∀ k, k < 15 → ∀ j, j < k → 0 < j → k ∣ 360360 ∧ 360360 / k * j ∈ S := by
    subst hS
    decide
  have P3 : ∀ a ∈ S, C.findIdx (fun l => l.contains a) < 13 ∧
      a ∈ C.getD (C.findIdx (fun l => l.contains a)) [] := by
    subst hS hC
    decide
  have P2 : ∀ i, i < 13 → ∀ a ∈ C.getD i [], ∀ b ∈ C.getD i [], a ≠ b →
      15 * a.gcd b ≤ a ∨ 15 * a.gcd b ≤ b := by
    subst hC
    decide
  have forms : ∀ x ∈ A.erase M, ∃ a ∈ S, 360360 * x = a * M := by
    intro x hx
    rw [Finset.mem_erase] at hx
    have hxpos : 0 < x := Nat.pos_of_ne_zero (fun h => hA (h ▸ hx.2))
    have hlt : x < M := lt_of_le_of_ne (hle x hx.2) hx.1
    have hg := hw x hx.2
    have hd1 := Nat.gcd_dvd_left M x
    have hd2 := Nat.gcd_dvd_right M x
    have hgpos : 0 < M.gcd x := Nat.gcd_pos_of_pos_right _ hxpos
    generalize M.gcd x = g at hg hd1 hd2 hgpos
    obtain ⟨k, hk⟩ := hd1
    obtain ⟨j, hj⟩ := hd2
    have hk15 : k < 15 := by
      by_contra hh
      push Not at hh
      have := Nat.mul_le_mul_left g hh
      omega
    have hjk : j < k := by
      by_contra hh
      push Not at hh
      have := Nat.mul_le_mul_left g hh
      omega
    have hj1 : 0 < j := by
      rcases Nat.eq_zero_or_pos j with h | h
      · subst h
        omega
      · exact h
    obtain ⟨hdvd, hmem⟩ := P1 k hk15 j hjk hj1
    refine ⟨360360 / k * j, hmem, ?_⟩
    obtain ⟨q, hq⟩ := hdvd
    have hkpos : 0 < k := by omega
    rw [hq, Nat.mul_div_cancel_left q hkpos, hk, hj]
    ring
  have hcard : (A.erase M).card = 14 := by
    rw [Finset.card_erase_of_mem hM, hn]
  have hmaps : ∀ x ∈ A.erase M, C.findIdx (fun l => l.contains (360360 * x / M)) ∈ Finset.range 13 := by
    intro x hx
    obtain ⟨a, ha, hax⟩ := forms x hx
    rw [Finset.mem_range, hax, Nat.mul_div_cancel _ hMpos]
    exact (P3 a ha).1
  obtain ⟨x, hx, y, hy, hxy, hc⟩ :=
    Finset.exists_ne_map_eq_of_card_lt_of_maps_to (by rw [hcard, Finset.card_range]; norm_num) hmaps
  obtain ⟨a, ha, hax⟩ := forms x hx
  obtain ⟨b, hb, hby⟩ := forms y hy
  simp only [hax, hby, Nat.mul_div_cancel _ hMpos] at hc
  have hab : a ≠ b := by
    intro h
    subst h
    apply hxy
    omega
  obtain ⟨hi, hai⟩ := P3 a ha
  obtain ⟨_, hbi⟩ := P3 b hb
  rw [← hc] at hbi
  have hgcd : a.gcd b * M = 360360 * x.gcd y := by
    have h1 : Nat.gcd (360360 * x) (360360 * y) = 360360 * x.gcd y := Nat.gcd_mul_left 360360 x y
    rw [hax, hby, Nat.gcd_mul_right] at h1
    exact h1
  have hxA := (Finset.mem_erase.mp hx).2
  have hyA := (Finset.mem_erase.mp hy).2
  rcases P2 _ hi a hai b hbi hab with h | h
  · refine ⟨x, hxA, y, hyA, key x y ?_⟩
    rw [hn]
    have h2 := Nat.mul_le_mul_right M h
    have h3 : x.gcd y * 15 * 360360 ≤ x * 360360 := by nlinarith
    exact Nat.le_of_mul_le_mul_right h3 (by norm_num)
  · refine ⟨y, hyA, x, hxA, key y x ?_⟩
    rw [hn, Nat.gcd_comm]
    have h2 := Nat.mul_le_mul_right M h
    have h3 : x.gcd y * 15 * 360360 ≤ y * 360360 := by nlinarith
    exact Nat.le_of_mul_le_mul_right h3 (by norm_num)
