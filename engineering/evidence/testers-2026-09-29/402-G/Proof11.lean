import Mathlib
import Nodes.«variant-7a4bb0cd».Context

/-! Graham's gcd conjecture (Erdős problem 402) for eleven-element sets. With M the largest
element, if gcd(M, x) > M/11 for every x then every other x is (j/k)M with j < k ≤ 10, so
L·x/M (L = lcm(1..10) = 2520) lies in a fixed set S of 31 values. S splits into 9 classes in
each of which any two distinct values c, d have 11·gcd(c, d) ≤ c or ≤ d; by pigeonhole two of
the 10 other elements share a class, and gcd(x, y)·L = gcd(c, d)·M transfers the bound. -/

theorem Opn.erdos_402_card_eleven :
    ∀ (A : Finset ℕ), 0 ∉ A → A.card = 11 → ∃ a ∈ A, ∃ b ∈ A, a.gcd b ≤ (a / A.card : ℚ) := by
  intro A hA hn
  have hpos : 0 < A.card := by omega
  have hne : A.Nonempty := Finset.card_pos.mp hpos
  have key : ∀ a b : ℕ, a.gcd b * A.card ≤ a → (a.gcd b : ℚ) ≤ (a / A.card : ℚ) := by
    intro a b h
    rw [le_div_iff₀ (by exact_mod_cast hpos)]
    exact_mod_cast h
  have hM : A.max' hne ∈ A := Finset.max'_mem A hne
  have hMpos : 0 < A.max' hne := Nat.pos_of_ne_zero (fun h => hA (h ▸ hM))
  by_cases hw : ∃ x ∈ A, (A.max' hne).gcd x * 11 ≤ A.max' hne
  · obtain ⟨x, hx, h⟩ := hw
    exact ⟨_, hM, x, hx, key _ x (by rw [hn]; exact h)⟩
  push_neg at hw
  have forms : ∀ x ∈ A.erase (A.max' hne), ∃ a ∈ ({252, 280, 315, 360, 420, 504, 560, 630, 720, 756, 840, 945, 1008, 1080, 1120, 1260, 1400, 1440, 1512, 1575, 1680, 1764, 1800, 1890, 1960, 2016, 2100, 2160, 2205, 2240, 2268} : Finset ℕ), 2520 * x = a * A.max' hne := by
    intro x hx
    rw [Finset.mem_erase] at hx
    have hxpos : 0 < x := Nat.pos_of_ne_zero (fun h => hA (h ▸ hx.2))
    have hlt : x < A.max' hne := lt_of_le_of_ne (Finset.le_max' A x hx.2) hx.1
    have hg := hw x hx.2
    obtain ⟨k, hk⟩ := Nat.gcd_dvd_left (A.max' hne) x
    obtain ⟨j, hj⟩ := Nat.gcd_dvd_right (A.max' hne) x
    have hgpos : 0 < (A.max' hne).gcd x := Nat.gcd_pos_of_pos_right _ hxpos
    have hkN : k < 11 := by
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
    refine ⟨2520 * j / k, ?_, ?_⟩
    · interval_cases k <;> interval_cases j <;> decide
    · interval_cases k <;> interval_cases j <;> omega
  have hcard : (A.erase (A.max' hne)).card = 10 := by
    rw [Finset.card_erase_of_mem hM, hn]
  have hS : ∀ a ∈ ({252, 280, 315, 360, 420, 504, 560, 630, 720, 756, 840, 945, 1008, 1080, 1120, 1260, 1400, 1440, 1512, 1575, 1680, 1764, 1800, 1890, 1960, 2016, 2100, 2160, 2205, 2240, 2268} : Finset ℕ), (fun a : ℕ => if a = 252 then 2 else if a = 280 then 6 else if a = 315 then 8 else if a = 360 then 7 else if a = 420 then 5 else if a = 504 then 4 else if a = 560 then 7 else if a = 630 then 3 else if a = 720 then 6 else if a = 756 then 6 else if a = 840 then 1 else if a = 945 then 2 else if a = 1008 then 5 else if a = 1080 then 5 else if a = 1120 then 3 else if a = 1260 then 0 else if a = 1400 then 4 else if a = 1440 then 4 else if a = 1512 then 3 else if a = 1575 then 1 else if a = 1680 then 2 else if a = 1764 then 7 else if a = 1800 then 2 else if a = 1890 then 4 else if a = 1960 then 0 else if a = 2016 then 1 else if a = 2100 then 6 else if a = 2160 then 0 else if a = 2205 then 5 else if a = 2240 then 5 else if a = 2268 then 8 else 0) a < 9 := by decide
  have hmaps : ∀ x ∈ A.erase (A.max' hne), (fun a : ℕ => if a = 252 then 2 else if a = 280 then 6 else if a = 315 then 8 else if a = 360 then 7 else if a = 420 then 5 else if a = 504 then 4 else if a = 560 then 7 else if a = 630 then 3 else if a = 720 then 6 else if a = 756 then 6 else if a = 840 then 1 else if a = 945 then 2 else if a = 1008 then 5 else if a = 1080 then 5 else if a = 1120 then 3 else if a = 1260 then 0 else if a = 1400 then 4 else if a = 1440 then 4 else if a = 1512 then 3 else if a = 1575 then 1 else if a = 1680 then 2 else if a = 1764 then 7 else if a = 1800 then 2 else if a = 1890 then 4 else if a = 1960 then 0 else if a = 2016 then 1 else if a = 2100 then 6 else if a = 2160 then 0 else if a = 2205 then 5 else if a = 2240 then 5 else if a = 2268 then 8 else 0) (2520 * x / A.max' hne) ∈ Finset.range 9 := by
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
  have hpair : ∀ a ∈ ({252, 280, 315, 360, 420, 504, 560, 630, 720, 756, 840, 945, 1008, 1080, 1120, 1260, 1400, 1440, 1512, 1575, 1680, 1764, 1800, 1890, 1960, 2016, 2100, 2160, 2205, 2240, 2268} : Finset ℕ), ∀ b ∈ ({252, 280, 315, 360, 420, 504, 560, 630, 720, 756, 840, 945, 1008, 1080, 1120, 1260, 1400, 1440, 1512, 1575, 1680, 1764, 1800, 1890, 1960, 2016, 2100, 2160, 2205, 2240, 2268} : Finset ℕ), a ≠ b → (fun a : ℕ => if a = 252 then 2 else if a = 280 then 6 else if a = 315 then 8 else if a = 360 then 7 else if a = 420 then 5 else if a = 504 then 4 else if a = 560 then 7 else if a = 630 then 3 else if a = 720 then 6 else if a = 756 then 6 else if a = 840 then 1 else if a = 945 then 2 else if a = 1008 then 5 else if a = 1080 then 5 else if a = 1120 then 3 else if a = 1260 then 0 else if a = 1400 then 4 else if a = 1440 then 4 else if a = 1512 then 3 else if a = 1575 then 1 else if a = 1680 then 2 else if a = 1764 then 7 else if a = 1800 then 2 else if a = 1890 then 4 else if a = 1960 then 0 else if a = 2016 then 1 else if a = 2100 then 6 else if a = 2160 then 0 else if a = 2205 then 5 else if a = 2240 then 5 else if a = 2268 then 8 else 0) a = (fun a : ℕ => if a = 252 then 2 else if a = 280 then 6 else if a = 315 then 8 else if a = 360 then 7 else if a = 420 then 5 else if a = 504 then 4 else if a = 560 then 7 else if a = 630 then 3 else if a = 720 then 6 else if a = 756 then 6 else if a = 840 then 1 else if a = 945 then 2 else if a = 1008 then 5 else if a = 1080 then 5 else if a = 1120 then 3 else if a = 1260 then 0 else if a = 1400 then 4 else if a = 1440 then 4 else if a = 1512 then 3 else if a = 1575 then 1 else if a = 1680 then 2 else if a = 1764 then 7 else if a = 1800 then 2 else if a = 1890 then 4 else if a = 1960 then 0 else if a = 2016 then 1 else if a = 2100 then 6 else if a = 2160 then 0 else if a = 2205 then 5 else if a = 2240 then 5 else if a = 2268 then 8 else 0) b →
      11 * a.gcd b ≤ a ∨ 11 * a.gcd b ≤ b := by decide
  have hgcd : a.gcd b * A.max' hne = 2520 * x.gcd y := by
    have h1 : Nat.gcd (2520 * x) (2520 * y) = 2520 * x.gcd y := Nat.gcd_mul_left 2520 x y
    rw [hax, hby, Nat.gcd_mul_right] at h1
    exact h1
  have hxA := (Finset.mem_erase.mp hx).2
  have hyA := (Finset.mem_erase.mp hy).2
  rcases hpair a ha b hb hab hc with h | h
  · refine ⟨x, hxA, y, hyA, key x y ?_⟩
    rw [hn]
    have h2 := Nat.mul_le_mul_right (A.max' hne) h
    have h3 : x.gcd y * 11 * 2520 ≤ x * 2520 := by nlinarith
    exact Nat.le_of_mul_le_mul_right h3 (by norm_num)
  · refine ⟨y, hyA, x, hxA, key y x ?_⟩
    rw [hn, Nat.gcd_comm]
    have h2 := Nat.mul_le_mul_right (A.max' hne) h
    have h3 : x.gcd y * 11 * 2520 ≤ y * 2520 := by nlinarith
    exact Nat.le_of_mul_le_mul_right h3 (by norm_num)
