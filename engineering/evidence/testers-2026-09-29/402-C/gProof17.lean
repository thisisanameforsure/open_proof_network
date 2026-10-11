import Mathlib

theorem Opn.erdos_402_card_seventeen :
    ∀ (A : Finset ℕ), 0 ∉ A → A.card = 17 → ∃ a ∈ A, ∃ b ∈ A, a.gcd b ≤ (a / A.card : ℚ) := by
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
  by_cases hw : ∃ x ∈ A, M.gcd x * 17 ≤ M
  · obtain ⟨x, hx, h⟩ := hw
    exact ⟨M, hM, x, hx, key M x (by rw [hn]; exact h)⟩
  push Not at hw
  obtain ⟨S, hS⟩ : ∃ S : List ℕ, S = [45045, 48048, 51480, 55440, 60060, 65520, 72072, 80080, 90090, 96096, 102960, 110880, 120120, 131040, 135135, 144144, 154440, 160160, 166320, 180180, 192192, 196560, 205920, 216216, 221760, 225225, 240240, 257400, 262080, 270270, 277200, 288288, 300300, 308880, 315315, 320320, 327600, 332640, 336336, 360360, 384384, 388080, 393120, 400400, 405405, 411840, 420420, 432432, 443520, 450450, 458640, 463320, 480480, 495495, 498960, 504504, 514800, 524160, 528528, 540540, 554400, 560560, 566280, 576576, 585585, 589680, 600600, 609840, 617760, 624624, 630630, 640640, 648648, 655200, 660660, 665280, 669240, 672672, 675675] := ⟨_, rfl⟩
  obtain ⟨C, hC⟩ : ∃ C : List (List ℕ), C = [[360360, 609840, 655200, 672672], [240240, 405405, 504504, 524160, 554400, 617760], [180180, 332640, 336336, 514800, 589680, 640640], [72072, 166320, 225225, 458640, 463320, 480480], [65520, 96096, 221760, 257400, 540540, 560560], [120120, 262080, 277200, 432432, 566280, 585585], [144144, 320320, 393120, 443520, 450450, 660660, 669240], [90090, 192192, 308880, 388080, 600600, 648648], [60060, 154440, 288288, 327600, 495495, 665280], [102960, 270270, 400400, 498960, 576576], [45045, 160160, 216216, 411840, 420420, 528528], [48048, 135135, 205920, 300300], [55440, 196560, 384384, 630630], [51480, 110880, 315315, 624624], [80080, 131040, 675675]] := ⟨_, rfl⟩
  have P1 : ∀ k, k < 17 → ∀ j, j < k → 0 < j → k ∣ 720720 ∧ 720720 / k * j ∈ S := by
    subst hS
    decide
  have P3 : ∀ a ∈ S, C.findIdx (fun l => l.contains a) < 15 ∧
      a ∈ C.getD (C.findIdx (fun l => l.contains a)) [] := by
    subst hS hC
    decide
  have P2 : ∀ i, i < 15 → ∀ a ∈ C.getD i [], ∀ b ∈ C.getD i [], a ≠ b →
      17 * a.gcd b ≤ a ∨ 17 * a.gcd b ≤ b := by
    subst hC
    decide
  have forms : ∀ x ∈ A.erase M, ∃ a ∈ S, 720720 * x = a * M := by
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
    have hk17 : k < 17 := by
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
    obtain ⟨hdvd, hmem⟩ := P1 k hk17 j hjk hj1
    refine ⟨720720 / k * j, hmem, ?_⟩
    obtain ⟨q, hq⟩ := hdvd
    have hkpos : 0 < k := by omega
    rw [hq, Nat.mul_div_cancel_left q hkpos, hk, hj]
    ring
  have hcard : (A.erase M).card = 16 := by
    rw [Finset.card_erase_of_mem hM, hn]
  have hmaps : ∀ x ∈ A.erase M, C.findIdx (fun l => l.contains (720720 * x / M)) ∈ Finset.range 15 := by
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
  have hgcd : a.gcd b * M = 720720 * x.gcd y := by
    have h1 : Nat.gcd (720720 * x) (720720 * y) = 720720 * x.gcd y := Nat.gcd_mul_left 720720 x y
    rw [hax, hby, Nat.gcd_mul_right] at h1
    exact h1
  have hxA := (Finset.mem_erase.mp hx).2
  have hyA := (Finset.mem_erase.mp hy).2
  rcases P2 _ hi a hai b hbi hab with h | h
  · refine ⟨x, hxA, y, hyA, key x y ?_⟩
    rw [hn]
    have h2 := Nat.mul_le_mul_right M h
    have h3 : x.gcd y * 17 * 720720 ≤ x * 720720 := by nlinarith
    exact Nat.le_of_mul_le_mul_right h3 (by norm_num)
  · refine ⟨y, hyA, x, hxA, key y x ?_⟩
    rw [hn, Nat.gcd_comm]
    have h2 := Nat.mul_le_mul_right M h
    have h3 : x.gcd y * 17 * 720720 ≤ y * 720720 := by nlinarith
    exact Nat.le_of_mul_le_mul_right h3 (by norm_num)
