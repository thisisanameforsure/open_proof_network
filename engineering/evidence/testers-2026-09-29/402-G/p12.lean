import Mathlib

/-! Graham's gcd conjecture (Erdős problem 402) for twelve-element sets. With M the largest
element, if gcd(M, x) > M/12 for every x then every other x is (j/k)M with j < k ≤ 11, so
L·x/M (L = lcm(1..11) = 27720) lies in a fixed set S of 41 values. S splits into 10 classes in
each of which any two distinct values c, d have 12·gcd(c, d) ≤ c or ≤ d; by pigeonhole two of
the 11 other elements share a class, and gcd(x, y)·L = gcd(c, d)·M transfers the bound. -/

theorem Opn.erdos_402_card_twelve :
    ∀ (A : Finset ℕ), 0 ∉ A → A.card = 12 → ∃ a ∈ A, ∃ b ∈ A, a.gcd b ≤ (a / A.card : ℚ) := by
  intro A hA hn
  have hpos : 0 < A.card := by omega
  have hne : A.Nonempty := Finset.card_pos.mp hpos
  have key : ∀ a b : ℕ, a.gcd b * A.card ≤ a → (a.gcd b : ℚ) ≤ (a / A.card : ℚ) := by
    intro a b h
    rw [le_div_iff₀ (by exact_mod_cast hpos)]
    exact_mod_cast h
  have hM : A.max' hne ∈ A := Finset.max'_mem A hne
  have hMpos : 0 < A.max' hne := Nat.pos_of_ne_zero (fun h => hA (h ▸ hM))
  by_cases hw : ∃ x ∈ A, (A.max' hne).gcd x * 12 ≤ A.max' hne
  · obtain ⟨x, hx, h⟩ := hw
    exact ⟨_, hM, x, hx, key _ x (by rw [hn]; exact h)⟩
  push_neg at hw
  have forms : ∀ x ∈ A.erase (A.max' hne), ∃ a ∈ ({2520, 2772, 3080, 3465, 3960, 4620, 5040, 5544, 6160, 6930, 7560, 7920, 8316, 9240, 10080, 10395, 11088, 11880, 12320, 12600, 13860, 15120, 15400, 15840, 16632, 17325, 17640, 18480, 19404, 19800, 20160, 20790, 21560, 22176, 22680, 23100, 23760, 24255, 24640, 24948, 25200} : Finset ℕ), 27720 * x = a * A.max' hne := by
    intro x hx
    rw [Finset.mem_erase] at hx
    have hxpos : 0 < x := Nat.pos_of_ne_zero (fun h => hA (h ▸ hx.2))
    have hlt : x < A.max' hne := lt_of_le_of_ne (Finset.le_max' A x hx.2) hx.1
    have hg := hw x hx.2
    obtain ⟨k, hk⟩ := Nat.gcd_dvd_left (A.max' hne) x
    obtain ⟨j, hj⟩ := Nat.gcd_dvd_right (A.max' hne) x
    have hgpos : 0 < (A.max' hne).gcd x := Nat.gcd_pos_of_pos_right _ hxpos
    have hkN : k < 12 := by
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
    refine ⟨27720 * j / k, ?_, ?_⟩
    · interval_cases k <;> interval_cases j <;> decide
    · interval_cases k <;> interval_cases j <;> omega
  have hcard : (A.erase (A.max' hne)).card = 11 := by
    rw [Finset.card_erase_of_mem hM, hn]
  have hS : ∀ a ∈ ({2520, 2772, 3080, 3465, 3960, 4620, 5040, 5544, 6160, 6930, 7560, 7920, 8316, 9240, 10080, 10395, 11088, 11880, 12320, 12600, 13860, 15120, 15400, 15840, 16632, 17325, 17640, 18480, 19404, 19800, 20160, 20790, 21560, 22176, 22680, 23100, 23760, 24255, 24640, 24948, 25200} : Finset ℕ), (fun a : ℕ => if a = 2520 then 2 else if a = 2772 then 7 else if a = 3080 then 6 else if a = 3465 then 9 else if a = 3960 then 8 else if a = 4620 then 5 else if a = 5040 then 5 else if a = 5544 then 4 else if a = 6160 then 7 else if a = 6930 then 3 else if a = 7560 then 3 else if a = 7920 then 9 else if a = 8316 then 2 else if a = 9240 then 1 else if a = 10080 then 1 else if a = 10395 then 6 else if a = 11088 then 6 else if a = 11880 then 7 else if a = 12320 then 4 else if a = 12600 then 4 else if a = 13860 then 0 else if a = 15120 then 0 else if a = 15400 then 3 else if a = 15840 then 5 else if a = 16632 then 5 else if a = 17325 then 1 else if a = 17640 then 6 else if a = 18480 then 2 else if a = 19404 then 1 else if a = 19800 then 2 else if a = 20160 then 7 else if a = 20790 then 4 else if a = 21560 then 0 else if a = 22176 then 3 else if a = 22680 then 8 else if a = 23100 then 6 else if a = 23760 then 1 else if a = 24255 then 2 else if a = 24640 then 5 else if a = 24948 then 9 else if a = 25200 then 9 else 0) a < 10 := by decide
  have hmaps : ∀ x ∈ A.erase (A.max' hne), (fun a : ℕ => if a = 2520 then 2 else if a = 2772 then 7 else if a = 3080 then 6 else if a = 3465 then 9 else if a = 3960 then 8 else if a = 4620 then 5 else if a = 5040 then 5 else if a = 5544 then 4 else if a = 6160 then 7 else if a = 6930 then 3 else if a = 7560 then 3 else if a = 7920 then 9 else if a = 8316 then 2 else if a = 9240 then 1 else if a = 10080 then 1 else if a = 10395 then 6 else if a = 11088 then 6 else if a = 11880 then 7 else if a = 12320 then 4 else if a = 12600 then 4 else if a = 13860 then 0 else if a = 15120 then 0 else if a = 15400 then 3 else if a = 15840 then 5 else if a = 16632 then 5 else if a = 17325 then 1 else if a = 17640 then 6 else if a = 18480 then 2 else if a = 19404 then 1 else if a = 19800 then 2 else if a = 20160 then 7 else if a = 20790 then 4 else if a = 21560 then 0 else if a = 22176 then 3 else if a = 22680 then 8 else if a = 23100 then 6 else if a = 23760 then 1 else if a = 24255 then 2 else if a = 24640 then 5 else if a = 24948 then 9 else if a = 25200 then 9 else 0) (27720 * x / A.max' hne) ∈ Finset.range 10 := by
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
  have hpair : ∀ a ∈ ({2520, 2772, 3080, 3465, 3960, 4620, 5040, 5544, 6160, 6930, 7560, 7920, 8316, 9240, 10080, 10395, 11088, 11880, 12320, 12600, 13860, 15120, 15400, 15840, 16632, 17325, 17640, 18480, 19404, 19800, 20160, 20790, 21560, 22176, 22680, 23100, 23760, 24255, 24640, 24948, 25200} : Finset ℕ), ∀ b ∈ ({2520, 2772, 3080, 3465, 3960, 4620, 5040, 5544, 6160, 6930, 7560, 7920, 8316, 9240, 10080, 10395, 11088, 11880, 12320, 12600, 13860, 15120, 15400, 15840, 16632, 17325, 17640, 18480, 19404, 19800, 20160, 20790, 21560, 22176, 22680, 23100, 23760, 24255, 24640, 24948, 25200} : Finset ℕ), a ≠ b → (fun a : ℕ => if a = 2520 then 2 else if a = 2772 then 7 else if a = 3080 then 6 else if a = 3465 then 9 else if a = 3960 then 8 else if a = 4620 then 5 else if a = 5040 then 5 else if a = 5544 then 4 else if a = 6160 then 7 else if a = 6930 then 3 else if a = 7560 then 3 else if a = 7920 then 9 else if a = 8316 then 2 else if a = 9240 then 1 else if a = 10080 then 1 else if a = 10395 then 6 else if a = 11088 then 6 else if a = 11880 then 7 else if a = 12320 then 4 else if a = 12600 then 4 else if a = 13860 then 0 else if a = 15120 then 0 else if a = 15400 then 3 else if a = 15840 then 5 else if a = 16632 then 5 else if a = 17325 then 1 else if a = 17640 then 6 else if a = 18480 then 2 else if a = 19404 then 1 else if a = 19800 then 2 else if a = 20160 then 7 else if a = 20790 then 4 else if a = 21560 then 0 else if a = 22176 then 3 else if a = 22680 then 8 else if a = 23100 then 6 else if a = 23760 then 1 else if a = 24255 then 2 else if a = 24640 then 5 else if a = 24948 then 9 else if a = 25200 then 9 else 0) a = (fun a : ℕ => if a = 2520 then 2 else if a = 2772 then 7 else if a = 3080 then 6 else if a = 3465 then 9 else if a = 3960 then 8 else if a = 4620 then 5 else if a = 5040 then 5 else if a = 5544 then 4 else if a = 6160 then 7 else if a = 6930 then 3 else if a = 7560 then 3 else if a = 7920 then 9 else if a = 8316 then 2 else if a = 9240 then 1 else if a = 10080 then 1 else if a = 10395 then 6 else if a = 11088 then 6 else if a = 11880 then 7 else if a = 12320 then 4 else if a = 12600 then 4 else if a = 13860 then 0 else if a = 15120 then 0 else if a = 15400 then 3 else if a = 15840 then 5 else if a = 16632 then 5 else if a = 17325 then 1 else if a = 17640 then 6 else if a = 18480 then 2 else if a = 19404 then 1 else if a = 19800 then 2 else if a = 20160 then 7 else if a = 20790 then 4 else if a = 21560 then 0 else if a = 22176 then 3 else if a = 22680 then 8 else if a = 23100 then 6 else if a = 23760 then 1 else if a = 24255 then 2 else if a = 24640 then 5 else if a = 24948 then 9 else if a = 25200 then 9 else 0) b →
      12 * a.gcd b ≤ a ∨ 12 * a.gcd b ≤ b := by decide
  have hgcd : a.gcd b * A.max' hne = 27720 * x.gcd y := by
    have h1 : Nat.gcd (27720 * x) (27720 * y) = 27720 * x.gcd y := Nat.gcd_mul_left 27720 x y
    rw [hax, hby, Nat.gcd_mul_right] at h1
    exact h1
  have hxA := (Finset.mem_erase.mp hx).2
  have hyA := (Finset.mem_erase.mp hy).2
  rcases hpair a ha b hb hab hc with h | h
  · refine ⟨x, hxA, y, hyA, key x y ?_⟩
    rw [hn]
    have h2 := Nat.mul_le_mul_right (A.max' hne) h
    have h3 : x.gcd y * 12 * 27720 ≤ x * 27720 := by nlinarith
    exact Nat.le_of_mul_le_mul_right h3 (by norm_num)
  · refine ⟨y, hyA, x, hxA, key y x ?_⟩
    rw [hn, Nat.gcd_comm]
    have h2 := Nat.mul_le_mul_right (A.max' hne) h
    have h3 : x.gcd y * 12 * 27720 ≤ y * 27720 := by nlinarith
    exact Nat.le_of_mul_le_mul_right h3 (by norm_num)
