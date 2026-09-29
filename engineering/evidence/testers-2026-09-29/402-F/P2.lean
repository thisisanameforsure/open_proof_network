import Mathlib

/-! A reduction of every fixed-size case of Erdős problem 402 (Graham's gcd problem) to a finite
certificate. With M the largest element of A, if gcd(M, x) ≤ M/n for some x the pair (M, x)
answers; otherwise every other element x is (j/k)·M with 1 ≤ j < k < n, so L·x = a·M for the
value a = L·j/k in S. The n − 1 other elements land on distinct values of S, and a colouring c
of S with n − 2 colours whose equal-coloured pairs a ≠ b all have n·gcd(a, b) ≤ max(a, b) gives,
by pigeonhole, two elements x, y with n·gcd(x, y) ≤ x or ≤ y, because gcd(a, b)·M = L·gcd(x, y).
A card-n variant then needs only L, S and c, and three decidable checks. -/

theorem Opn.erdos_402_card_of_colouring :
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
