import Mathlib
import Nodes.«variant-892f5809».Context

/-! Graham's gcd conjecture (Erdős problem 402) for 9-element sets: with M the largest element,
if every b had gcd(M, b) > M/9 then every other element would be (j/k)M with j < k < 9, and a
colouring of those values into 7 classes, each a set of pairwise "good" values, shows the
8 other elements cannot all avoid a pair x, y with 9 * gcd(x, y) ≤ max(x, y). -/

theorem Opn.erdos_402_card_nine :
    ∀ (A : Finset ℕ), 0 ∉ A → A.card = 9 → ∃ a ∈ A, ∃ b ∈ A, a.gcd b ≤ (a / A.card : ℚ) := by
  intro A h0 hcard
  have toQ : ∀ a b : ℕ, 9 * a.gcd b ≤ a → (a.gcd b : ℚ) ≤ (a / A.card : ℚ) := by
    intro a b hab
    have h9 : ((A.card : ℕ) : ℚ) = 9 := by rw [hcard]; norm_num
    rw [h9, le_div_iff₀ (by norm_num : (0 : ℚ) < 9)]
    exact_mod_cast (by omega : a.gcd b * 9 ≤ a)
  have hne : A.Nonempty := Finset.card_pos.mp (by omega)
  have hMA : A.max' hne ∈ A := Finset.max'_mem A hne
  have hMpos : 0 < A.max' hne := Nat.pos_of_ne_zero fun h => h0 (h ▸ hMA)
  by_cases hdirect : ∃ x ∈ A, 9 * (A.max' hne).gcd x ≤ A.max' hne
  · obtain ⟨x, hxA, hx⟩ := hdirect
    exact ⟨A.max' hne, hMA, x, hxA, toQ _ x hx⟩
  push_neg at hdirect
  -- every other element x satisfies 840 x = c M with c = 840 j / k, 1 ≤ j < k ≤ 8
  have hval : ∀ x ∈ A.erase (A.max' hne), ∃ c ∈ [105, 120, 140, 168, 210, 240, 280, 315, 336, 360,
      420, 480, 504, 525, 560, 600, 630, 672, 700, 720, 735], 840 * x = c * A.max' hne := by
    intro x hx
    obtain ⟨hxM, hxA⟩ := Finset.mem_erase.mp hx
    have hxpos : 0 < x := Nat.pos_of_ne_zero fun h => h0 (h ▸ hxA)
    have hxlt : x < A.max' hne := lt_of_le_of_ne (Finset.le_max' A x hxA) hxM
    have hbig : A.max' hne < 9 * (A.max' hne).gcd x := hdirect x hxA
    obtain ⟨k, hk⟩ := Nat.gcd_dvd_left (A.max' hne) x
    obtain ⟨j, hj⟩ := Nat.gcd_dvd_right (A.max' hne) x
    have hgpos : 0 < (A.max' hne).gcd x := Nat.gcd_pos_of_pos_right _ hxpos
    have hk9 : k < 9 := by
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
    refine ⟨840 * j / k, ?_, ?_⟩
    · interval_cases k <;> interval_cases j <;> decide
    · interval_cases k <;> interval_cases j <;> omega
  -- the colouring: seven classes, each pairwise good
  have hpair : ∀ a ∈ [105, 120, 140, 168, 210, 240, 280, 315, 336, 360,
      420, 480, 504, 525, 560, 600, 630, 672, 700, 720, 735],
      ∀ b ∈ [105, 120, 140, 168, 210, 240, 280, 315, 336, 360,
      420, 480, 504, 525, 560, 600, 630, 672, 700, 720, 735],
      (if a = 420 ∨ a = 600 then 0 else if a = 210 ∨ a = 360 ∨ a = 672 ∨ a = 700 then 1
        else if a = 120 ∨ a = 560 ∨ a = 630 then 2 else if a = 105 ∨ a = 240 ∨ a = 504 then 3
        else if a = 280 ∨ a = 315 ∨ a = 480 then 4 else if a = 168 ∨ a = 525 ∨ a = 720 then 5
        else 6) =
      (if b = 420 ∨ b = 600 then 0 else if b = 210 ∨ b = 360 ∨ b = 672 ∨ b = 700 then 1
        else if b = 120 ∨ b = 560 ∨ b = 630 then 2 else if b = 105 ∨ b = 240 ∨ b = 504 then 3
        else if b = 280 ∨ b = 315 ∨ b = 480 then 4 else if b = 168 ∨ b = 525 ∨ b = 720 then 5
        else 6) →
      a = b ∨ 9 * a.gcd b ≤ a ∨ 9 * a.gcd b ≤ b := by
    decide
  sorry
