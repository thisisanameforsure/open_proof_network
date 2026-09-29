import Mathlib
import Nodes.«variant-4ad214d0».Context

/-! Graham's gcd conjecture (Erdős problem 402) restricted to sets of exactly fifteen elements.
Route: let M be the largest element. Either some x has 15 · gcd(M, x) ≤ M, and the pair (M, x)
works, or every other x has M < 15 · gcd(M, x), so M = k·g and x = j·g with g = gcd(M, x) and
1 ≤ j < k ≤ 14; then 360360 · x / M (360360 = lcm(1..14)) takes one of 63 values. A computer
search finds a split of those 63 values into 13 classes in each of which two distinct values
c, d satisfy 15 · gcd(c, d) ≤ max(c, d); fourteen elements in thirteen classes force two into one
class, and gcd(x, y) · 360360 = gcd(c, d) · M carries the bound back to x and y. -/

theorem Opn.erdos_402_card_fifteen :
    ∀ (A : Finset ℕ), 0 ∉ A → A.card = 15 → ∃ a ∈ A, ∃ b ∈ A, a.gcd b ≤ (a / A.card : ℚ) := by
  intro A h0 hcard
  have toQ : ∀ a b : ℕ, 15 * a.gcd b ≤ a → (a.gcd b : ℚ) ≤ (a / A.card : ℚ) := by
    intro a b hab
    have hN : ((A.card : ℕ) : ℚ) = 15 := by rw [hcard]; norm_num
    rw [hN, le_div_iff₀ (by norm_num : (0 : ℚ) < 15)]
    exact_mod_cast (by omega : a.gcd b * 15 ≤ a)
  have hne : A.Nonempty := Finset.card_pos.mp (by omega)
  have hMA : A.max' hne ∈ A := Finset.max'_mem A hne
  have hMpos : 0 < A.max' hne := Nat.pos_of_ne_zero fun h => h0 (h ▸ hMA)
  by_cases hdirect : ∃ x ∈ A, 15 * (A.max' hne).gcd x ≤ A.max' hne
  · obtain ⟨x, hxA, hx⟩ := hdirect
    exact ⟨A.max' hne, hMA, x, hxA, toQ _ x hx⟩
  simp only [not_exists, not_and, not_le] at hdirect
  -- every other element x has 360360 x = c M with c = 360360 j / k, 1 ≤ j < k ≤ 14
  have hval : ∀ x ∈ A.erase (A.max' hne), ∃ c ∈ ([25740, 27720, 30030, 32760, 36036, 40040, 45045, 51480, 55440, 60060, 65520, 72072,
      77220, 80080, 83160, 90090, 98280, 102960, 108108, 110880, 120120, 128700, 131040,
      135135, 138600, 144144, 150150, 154440, 160160, 163800, 166320, 180180, 194040, 196560,
      200200, 205920, 210210, 216216, 221760, 225225, 229320, 231660, 240240, 249480, 252252,
      257400, 262080, 270270, 277200, 280280, 283140, 288288, 294840, 300300, 304920, 308880,
      315315, 320320, 324324, 327600, 330330, 332640, 334620] : List ℕ),
      360360 * x = c * A.max' hne := by
    intro x hx
    obtain ⟨hxM, hxA⟩ := Finset.mem_erase.mp hx
    have hxpos : 0 < x := Nat.pos_of_ne_zero fun h => h0 (h ▸ hxA)
    have hxlt : x < A.max' hne := lt_of_le_of_ne (Finset.le_max' A x hxA) hxM
    have hbig : A.max' hne < 15 * (A.max' hne).gcd x := hdirect x hxA
    obtain ⟨k, hk⟩ := Nat.gcd_dvd_left (A.max' hne) x
    obtain ⟨j, hj⟩ := Nat.gcd_dvd_right (A.max' hne) x
    have hgpos : 0 < (A.max' hne).gcd x := Nat.gcd_pos_of_pos_right _ hxpos
    have hkN : k < 15 := by
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
    refine ⟨360360 * j / k, ?_, ?_⟩
    · interval_cases k <;> interval_cases j <;> decide
    · interval_cases k <;> interval_cases j <;> omega
  -- a split of the 63 values into 13 classes, each pairwise good (found by computer search)
  obtain ⟨cls, hcls⟩ : ∃ cls : ℕ → List ℕ, cls = fun i => [[180180, 221760, 294840],
      [120120, 166320, 225225, 231660, 252252, 327600],
      [90090, 196560, 200200, 205920, 304920, 324324],
      [32760, 77220, 240240, 249480, 315315],
      [60060, 138600, 154440, 229320, 288288],
      [51480, 108108, 110880, 150150, 262080, 280280],
      [30030, 102960, 163800, 194040, 216216, 320320],
      [72072, 160160, 270270, 277200, 283140],
      [40040, 55440, 131040, 135135, 300300, 308880],
      [27720, 98280, 144144, 210210, 257400],
      [36036, 65520, 83160, 128700, 330330],
      [25740, 80080, 332640],
      [45045, 334620]].getD i [] :=
    ⟨_, rfl⟩
  obtain ⟨col, hcol⟩ : ∃ col : ℕ → ℕ, col = fun c => [[180180, 221760, 294840],
      [120120, 166320, 225225, 231660, 252252, 327600],
      [90090, 196560, 200200, 205920, 304920, 324324],
      [32760, 77220, 240240, 249480, 315315],
      [60060, 138600, 154440, 229320, 288288],
      [51480, 108108, 110880, 150150, 262080, 280280],
      [30030, 102960, 163800, 194040, 216216, 320320],
      [72072, 160160, 270270, 277200, 283140],
      [40040, 55440, 131040, 135135, 300300, 308880],
      [27720, 98280, 144144, 210210, 257400],
      [36036, 65520, 83160, 128700, 330330],
      [25740, 80080, 332640],
      [45045, 334620]].findIdx
      (fun D => D.contains c) := ⟨_, rfl⟩
  have hcover : ∀ c ∈ ([25740, 27720, 30030, 32760, 36036, 40040, 45045, 51480, 55440, 60060, 65520, 72072,
      77220, 80080, 83160, 90090, 98280, 102960, 108108, 110880, 120120, 128700, 131040,
      135135, 138600, 144144, 150150, 154440, 160160, 163800, 166320, 180180, 194040, 196560,
      200200, 205920, 210210, 216216, 221760, 225225, 229320, 231660, 240240, 249480, 252252,
      257400, 262080, 270270, 277200, 280280, 283140, 288288, 294840, 300300, 304920, 308880,
      315315, 320320, 324324, 327600, 330330, 332640, 334620] : List ℕ),
      col c < 13 ∧ c ∈ cls (col c) := by
    subst hcol hcls
    decide
  have hgood : ∀ i < 13, ∀ c ∈ cls i, ∀ d ∈ cls i, c = d ∨ 15 * c.gcd d ≤ c ∨ 15 * c.gcd d ≤ d := by
    subst hcls
    decide
  -- pigeonhole: 14 other elements, 13 classes
  have hmaps : ∀ x ∈ A.erase (A.max' hne), col (360360 * x / A.max' hne) ∈ Finset.range 13 := by
    intro x hx
    obtain ⟨c, hc, hxc⟩ := hval x hx
    rw [Finset.mem_range, hxc, Nat.mul_div_cancel _ hMpos]
    exact (hcover c hc).1
  have hlt : (Finset.range 13).card < (A.erase (A.max' hne)).card := by
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
  have hg : c.gcd d * A.max' hne = 360360 * x.gcd y := by
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
