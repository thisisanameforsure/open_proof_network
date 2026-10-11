import Mathlib
import Nodes.«variant-b89de5c4».Context

/-! Graham's gcd conjecture (Erdős problem 402) for eighteen-element sets. With M the largest
element, if gcd(M, x) > M/18 for every x then every other x is (j/k)M with j < k ≤ 17, so
L·x/M (L = lcm(1..17) = 12252240) lies in a fixed set S of 95 values. S splits into 16 classes in
each of which any two distinct values c, d have 18·gcd(c, d) ≤ c or ≤ d; by pigeonhole two of
the 17 other elements share a class, and gcd(x, y)·L = gcd(c, d)·M transfers the bound. -/

theorem Opn.erdos_402_card_eighteen :
    ∀ (A : Finset ℕ), 0 ∉ A → A.card = 18 → ∃ a ∈ A, ∃ b ∈ A, a.gcd b ≤ (a / A.card : ℚ) := by
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
  exact red 18 12252240 {720720, 765765, 816816, 875160, 942480, 1021020, 1113840, 1225224, 1361360, 1441440, 1531530, 1633632, 1750320, 1884960, 2042040, 2162160, 2227680, 2297295, 2450448, 2625480, 2722720, 2827440, 2882880, 3063060, 3267264, 3341520, 3500640, 3603600, 3675672, 3769920, 3828825, 4084080, 4324320, 4375800, 4455360, 4594590, 4712400, 4900896, 5045040, 5105100, 5250960, 5360355, 5445440, 5569200, 5654880, 5717712, 5765760, 6126120, 6486480, 6534528, 6597360, 6683040, 6806800, 6891885, 7001280, 7147140, 7207200, 7351344, 7539840, 7657650, 7796880, 7876440, 7927920, 8168160, 8423415, 8482320, 8576568, 8648640, 8751600, 8910720, 8984976, 9189180, 9369360, 9424800, 9529520, 9626760, 9801792, 9954945, 10024560, 10090080, 10210200, 10367280, 10501920, 10618608, 10720710, 10810800, 10890880, 11027016, 11138400, 11231220, 11309760, 11377080, 11435424, 11486475, 11531520}
    (fun a : ℕ => if a = 720720 then 12 else if a = 765765 then 10 else if a = 816816 then 13 else if a = 875160 then 14 else if a = 942480 then 4 else if a = 1021020 then 7 else if a = 1113840 then 9 else if a = 1225224 then 3 else if a = 1361360 then 15 else if a = 1441440 then 13 else if a = 1531530 then 8 else if a = 1633632 then 4 else if a = 1750320 then 11 else if a = 1884960 then 14 else if a = 2042040 then 5 else if a = 2162160 then 3 else if a = 2227680 then 12 else if a = 2297295 then 11 else if a = 2450448 then 6 else if a = 2625480 then 7 else if a = 2722720 then 9 else if a = 2827440 then 12 else if a = 2882880 then 11 else if a = 3063060 then 2 else if a = 3267264 then 8 else if a = 3341520 then 13 else if a = 3500640 then 10 else if a = 3603600 then 4 else if a = 3675672 then 10 else if a = 3769920 then 5 else if a = 3828825 then 3 else if a = 4084080 then 1 else if a = 4324320 then 2 else if a = 4375800 then 9 else if a = 4455360 then 14 else if a = 4594590 then 9 else if a = 4712400 then 7 else if a = 4900896 then 7 else if a = 5045040 then 7 else if a = 5105100 then 10 else if a = 5250960 then 8 else if a = 5360355 then 12 else if a = 5445440 then 6 else if a = 5569200 then 5 else if a = 5654880 then 10 else if a = 5717712 then 2 else if a = 5765760 then 5 else if a = 6126120 then 0 else if a = 6486480 then 6 else if a = 6534528 then 11 else if a = 6597360 then 6 else if a = 6683040 then 6 else if a = 6806800 then 11 else if a = 6891885 then 7 else if a = 7001280 then 4 else if a = 7147140 then 11 else if a = 7207200 then 1 else if a = 7351344 then 5 else if a = 7539840 then 1 else if a = 7657650 then 6 else if a = 7796880 then 3 else if a = 7876440 then 3 else if a = 7927920 then 0 else if a = 8168160 then 3 else if a = 8423415 then 13 else if a = 8482320 then 8 else if a = 8576568 then 1 else if a = 8648640 then 8 else if a = 8751600 then 2 else if a = 8910720 then 2 else if a = 8984976 then 10 else if a = 9189180 then 4 else if a = 9369360 then 10 else if a = 9424800 then 0 else if a = 9529520 then 4 else if a = 9626760 then 6 else if a = 9801792 then 9 else if a = 9954945 then 1 else if a = 10024560 then 0 else if a = 10090080 then 14 else if a = 10210200 then 8 else if a = 10367280 then 2 else if a = 10501920 then 1 else if a = 10618608 then 12 else if a = 10720710 then 5 else if a = 10810800 then 9 else if a = 10890880 then 7 else if a = 11027016 then 2 else if a = 11138400 then 4 else if a = 11231220 then 9 else if a = 11309760 then 3 else if a = 11377080 then 5 else if a = 11435424 then 0 else if a = 11486475 then 14 else if a = 11531520 then 15 else 0)
    (by norm_num) (by norm_num) (by decide +kernel) (by decide +kernel) (by decide +kernel) A hA hn
