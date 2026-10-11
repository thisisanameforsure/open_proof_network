import Mathlib
import Nodes.«variant-a5969ff3».Context

/-! Graham's gcd conjecture (Erdős problem 402) for 10-element sets: with M the largest element,
if every b had gcd(M, b) > M/10 then every other element would be (j/k)M with j < k < 10, and a
colouring of those values into 8 classes, each a set of pairwise "good" values, shows the
9 other elements cannot all avoid a pair x, y with 10 * gcd(x, y) ≤ max(x, y). -/

theorem Opn.erdos_402_card_ten :
    ∀ (A : Finset ℕ), 0 ∉ A → A.card = 10 → ∃ a ∈ A, ∃ b ∈ A, a.gcd b ≤ (a / A.card : ℚ) := by
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
  exact red 10 2520 {280, 315, 360, 420, 504, 560, 630, 720, 840, 945, 1008, 1080, 1120, 1260, 1400, 1440, 1512, 1575, 1680, 1800, 1890, 1960, 2016, 2100, 2160, 2205, 2240}
    (fun a : ℕ => if a = 280 then 4 else if a = 315 then 6 else if a = 360 then 2 else if a = 420 then 5 else if a = 504 then 7 else if a = 560 then 6 else if a = 630 then 3 else if a = 720 then 5 else if a = 840 then 1 else if a = 945 then 2 else if a = 1008 then 4 else if a = 1080 then 3 else if a = 1120 then 3 else if a = 1260 then 0 else if a = 1400 then 0 else if a = 1440 then 4 else if a = 1512 then 5 else if a = 1575 then 5 else if a = 1680 then 2 else if a = 1800 then 1 else if a = 1890 then 4 else if a = 1960 then 5 else if a = 2016 then 1 else if a = 2100 then 3 else if a = 2160 then 0 else if a = 2205 then 1 else if a = 2240 then 7 else 0)
    (by norm_num) (by norm_num) (by decide) (by decide) (by decide) A hA hn
