import Mathlib

/-! Graham's gcd conjecture (Erdős problem 402) restricted to sets of exactly seventeen elements.
Route: let M be the largest element. Either some x has 17 · gcd(M, x) ≤ M, and the pair (M, x)
works, or every other x has M < 17 · gcd(M, x), so M = k·g and x = j·g with g = gcd(M, x) and
1 ≤ j < k ≤ 16; then 720720 · x / M (720720 = lcm(1..16)) takes one of 79 values. A computer
search finds a split of those 79 values into 15 classes in each of which two distinct values
c, d satisfy 17 · gcd(c, d) ≤ max(c, d); sixteen elements in fifteen classes force two into one
class, and gcd(x, y) · 720720 = gcd(c, d) · M carries the bound back to x and y. -/

theorem Opn.erdos_402_card_seventeen :
    ∀ (A : Finset ℕ), 0 ∉ A → A.card = 17 → ∃ a ∈ A, ∃ b ∈ A, a.gcd b ≤ (a / A.card : ℚ) := by
  intro A h0 hcard
  have toQ : ∀ a b : ℕ, 17 * a.gcd b ≤ a → (a.gcd b : ℚ) ≤ (a / A.card : ℚ) := by
    intro a b hab
    have hN : ((A.card : ℕ) : ℚ) = 17 := by rw [hcard]; norm_num
    rw [hN, le_div_iff₀ (by norm_num : (0 : ℚ) < 17)]
    exact_mod_cast (by omega : a.gcd b * 17 ≤ a)
  have hne : A.Nonempty := Finset.card_pos.mp (by omega)
  have hMA : A.max' hne ∈ A := Finset.max'_mem A hne
  have hMpos : 0 < A.max' hne := Nat.pos_of_ne_zero fun h => h0 (h ▸ hMA)
  by_cases hdirect : ∃ x ∈ A, 17 * (A.max' hne).gcd x ≤ A.max' hne
  · obtain ⟨x, hxA, hx⟩ := hdirect
    exact ⟨A.max' hne, hMA, x, hxA, toQ _ x hx⟩
  simp only [not_exists, not_and, not_le] at hdirect
  -- every other element x has 720720 x = c M with c = 720720 j / k, 1 ≤ j < k ≤ 16
  have hval : ∀ x ∈ A.erase (A.max' hne), ∃ c ∈ ([45045, 48048, 51480, 55440, 60060, 65520, 72072, 80080, 90090, 96096, 102960, 110880,
      120120, 131040, 135135, 144144, 154440, 160160, 166320, 180180, 192192, 196560, 205920,
      216216, 221760, 225225, 240240, 257400, 262080, 270270, 277200, 288288, 300300, 308880,
      315315, 320320, 327600, 332640, 336336, 360360, 384384, 388080, 393120, 400400, 405405,
      411840, 420420, 432432, 443520, 450450, 458640, 463320, 480480, 495495, 498960, 504504,
      514800, 524160, 528528, 540540, 554400, 560560, 566280, 576576, 585585, 589680, 600600,
      609840, 617760, 624624, 630630, 640640, 648648, 655200, 660660, 665280, 669240, 672672,
      675675] : List ℕ),
      720720 * x = c * A.max' hne := by
    intro x hx
    obtain ⟨hxM, hxA⟩ := Finset.mem_erase.mp hx
    have hxpos : 0 < x := Nat.pos_of_ne_zero fun h => h0 (h ▸ hxA)
    have hxlt : x < A.max' hne := lt_of_le_of_ne (Finset.le_max' A x hxA) hxM
    have hbig : A.max' hne < 17 * (A.max' hne).gcd x := hdirect x hxA
    obtain ⟨k, hk⟩ := Nat.gcd_dvd_left (A.max' hne) x
    obtain ⟨j, hj⟩ := Nat.gcd_dvd_right (A.max' hne) x
    have hgpos : 0 < (A.max' hne).gcd x := Nat.gcd_pos_of_pos_right _ hxpos
    have hkN : k < 17 := by
      by_contra hc
      have := Nat.mul_le_mul_left ((A.max' hne).gcd x) (not_lt.mp hc)
      omega
    have hjk : j < k := by
      by_contra hc
      have := Nat.mul_le_mul_left ((A.max' hne).gcd x) (not_lt.mp hc)
      omega
    have hj0 : 0 < j := by
      rcases Nat.eq_zero_or_pos j with h | h
      · rw [h, Nat.mul_zero] at hj
        omega
      · exact h
    refine ⟨720720 * j / k, ?_, ?_⟩
    · interval_cases k <;> interval_cases j <;> decide
    · interval_cases k <;> interval_cases j <;> omega
  -- a split of the 79 values into 15 classes, each pairwise good (found by computer search)
  obtain ⟨cls, hcls⟩ : ∃ cls : ℕ → List ℕ, cls = fun i => [[360360, 609840, 655200, 672672],
      [240240, 405405, 504504, 524160, 554400, 617760],
      [180180, 332640, 336336, 514800, 589680, 640640],
      [72072, 166320, 225225, 458640, 463320, 480480],
      [65520, 96096, 221760, 257400, 540540, 560560],
      [120120, 262080, 277200, 432432, 566280, 585585],
      [144144, 320320, 393120, 443520, 450450, 660660, 669240],
      [90090, 192192, 308880, 388080, 600600, 648648],
      [60060, 154440, 288288, 327600, 495495, 665280],
      [102960, 270270, 400400, 498960, 576576],
      [45045, 160160, 216216, 411840, 420420, 528528],
      [48048, 135135, 205920, 300300],
      [55440, 196560, 384384, 630630],
      [51480, 110880, 315315, 624624],
      [80080, 131040, 675675]].getD i [] :=
    ⟨_, rfl⟩
  obtain ⟨col, hcol⟩ : ∃ col : ℕ → ℕ, col = fun c => [[360360, 609840, 655200, 672672],
      [240240, 405405, 504504, 524160, 554400, 617760],
      [180180, 332640, 336336, 514800, 589680, 640640],
      [72072, 166320, 225225, 458640, 463320, 480480],
      [65520, 96096, 221760, 257400, 540540, 560560],
      [120120, 262080, 277200, 432432, 566280, 585585],
      [144144, 320320, 393120, 443520, 450450, 660660, 669240],
      [90090, 192192, 308880, 388080, 600600, 648648],
      [60060, 154440, 288288, 327600, 495495, 665280],
      [102960, 270270, 400400, 498960, 576576],
      [45045, 160160, 216216, 411840, 420420, 528528],
      [48048, 135135, 205920, 300300],
      [55440, 196560, 384384, 630630],
      [51480, 110880, 315315, 624624],
      [80080, 131040, 675675]].findIdx
      (fun D => D.contains c) := ⟨_, rfl⟩
  have hcover : ∀ c ∈ ([45045, 48048, 51480, 55440, 60060, 65520, 72072, 80080, 90090, 96096, 102960, 110880,
      120120, 131040, 135135, 144144, 154440, 160160, 166320, 180180, 192192, 196560, 205920,
      216216, 221760, 225225, 240240, 257400, 262080, 270270, 277200, 288288, 300300, 308880,
      315315, 320320, 327600, 332640, 336336, 360360, 384384, 388080, 393120, 400400, 405405,
      411840, 420420, 432432, 443520, 450450, 458640, 463320, 480480, 495495, 498960, 504504,
      514800, 524160, 528528, 540540, 554400, 560560, 566280, 576576, 585585, 589680, 600600,
      609840, 617760, 624624, 630630, 640640, 648648, 655200, 660660, 665280, 669240, 672672,
      675675] : List ℕ),
      col c < 15 ∧ c ∈ cls (col c) := by
    subst hcol hcls
    decide
  have hgood : ∀ i < 15, ∀ c ∈ cls i, ∀ d ∈ cls i, c = d ∨ 17 * c.gcd d ≤ c ∨ 17 * c.gcd d ≤ d := by
    subst hcls
    decide
  -- pigeonhole: 16 other elements, 15 classes
  have hmaps : ∀ x ∈ A.erase (A.max' hne), col (720720 * x / A.max' hne) ∈ Finset.range 15 := by
    intro x hx
    obtain ⟨c, hc, hxc⟩ := hval x hx
    rw [Finset.mem_range, hxc, Nat.mul_div_cancel _ hMpos]
    exact (hcover c hc).1
  have hlt : (Finset.range 15).card < (A.erase (A.max' hne)).card := by
    rw [Finset.card_erase_of_mem hMA, hcard, Finset.card_range]
    norm_num
  obtain ⟨x, hx, y, hy, hxy, hxycol⟩ := Finset.exists_ne_map_eq_of_card_lt_of_maps_to hlt hmaps
  obtain ⟨c, hc, hxc⟩ := hval x hx
  obtain ⟨d, hd, hyd⟩ := hval y hy
  rw [hxc, hyd, Nat.mul_div_cancel _ hMpos, Nat.mul_div_cancel _ hMpos] at hxycol
  have hcd : c ≠ d := by
    rintro rfl
    exact hxy (by omega)
  have hcmem := (hcover c hc).2
  have hdmem := (hcover d hd).2
  rw [← hxycol] at hdmem
  -- carry the good pair of values back to x and y
  have hg : c.gcd d * A.max' hne = 720720 * x.gcd y := by
    rw [← Nat.gcd_mul_right, ← hxc, ← hyd, Nat.gcd_mul_left]
  have hxA : x ∈ A := (Finset.mem_erase.mp hx).2
  have hyA : y ∈ A := (Finset.mem_erase.mp hy).2
  rcases hgood (col c) (hcover c hc).1 c hcmem d hdmem with h | h | h
  · exact absurd h hcd
  · refine ⟨x, hxA, y, hyA, toQ x y ?_⟩
    have h2 := Nat.mul_le_mul_right (A.max' hne) h
    rw [Nat.mul_assoc, hg, ← hxc] at h2
    omega
  · refine ⟨y, hyA, x, hxA, toQ y x ?_⟩
    have h2 := Nat.mul_le_mul_right (A.max' hne) h
    rw [Nat.mul_assoc, hg, ← hyd] at h2
    rw [Nat.gcd_comm]
    omega
