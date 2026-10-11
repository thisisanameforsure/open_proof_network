import Mathlib
import Nodes.«variant-6bb50ad7».Context

/-! Graham's gcd conjecture (Erdős problem 402) for eight-element sets. With M the largest
element, if gcd(M, b) > M/8 for every b then every other b is (j/k)M with j < k ≤ 7: one of
seventeen values. Among those, no seven avoid a pair x, y with x / gcd(x, y) ≥ 8 (a finite
case split on which values occur), so the seven other elements cannot all be distinct values. -/

theorem Opn.erdos_402_card_eight :
    ∀ (A : Finset ℕ), 0 ∉ A → A.card = 8 → ∃ a ∈ A, ∃ b ∈ A, a.gcd b ≤ (a / A.card : ℚ) := by
  intro A h0 hcard
  -- the rational inequality is 8 * gcd a b ≤ a
  have red : ∀ a b : ℕ, 8 * a.gcd b ≤ a → (a.gcd b : ℚ) ≤ (a / A.card : ℚ) := by
    intro a b h
    rw [hcard, le_div_iff₀ (by norm_num)]
    exact_mod_cast (by omega : a.gcd b * 8 ≤ a)
  have hne : A.Nonempty := Finset.card_pos.mp (by omega)
  obtain ⟨M, hMA, hMmax⟩ : ∃ M ∈ A, ∀ x ∈ A, x ≤ M :=
    ⟨A.max' hne, A.max'_mem hne, fun x hx => A.le_max' x hx⟩
  have hMpos : 0 < M := Nat.pos_of_ne_zero (by rintro rfl; exact h0 hMA)
  by_cases hsmall : ∃ x ∈ A, 8 * M.gcd x ≤ M
  · obtain ⟨x, hx, h⟩ := hsmall
    exact ⟨M, hMA, x, hx, red M x h⟩
  push Not at hsmall
  -- the values L * j / k (0 < j < k < 8) all lie in the list, and every k < 8 divides L
  have hmemV : ∀ k < 8, ∀ j < k, 0 < j → 420 * j / k ∈ ({60, 70, 84, 105, 120, 140, 168, 180, 210, 240, 252, 280, 300, 315, 336, 350, 360} : Finset ℕ) := by decide +kernel
  have hdvd : ∀ k < 8, 0 < k → k ∣ 420 := by decide +kernel
  -- every other element x has 420 * x = v * M for one of the 17 values v = 420 * j / k
  have hval : ∀ x ∈ A.erase M, ∃ v ∈ ({60, 70, 84, 105, 120, 140, 168, 180, 210, 240, 252, 280, 300, 315, 336, 350, 360} : Finset ℕ), 420 * x = v * M := by
    intro x hx
    obtain ⟨hxM, hxA⟩ := Finset.mem_erase.mp hx
    have hxpos : 0 < x := Nat.pos_of_ne_zero (by rintro rfl; exact h0 hxA)
    have hlt : x < M := lt_of_le_of_ne (hMmax x hxA) hxM
    have hbig : M < 8 * M.gcd x := hsmall x hxA
    obtain ⟨k, hk⟩ := Nat.gcd_dvd_left M x
    obtain ⟨j, hj⟩ := Nat.gcd_dvd_right M x
    have hkN : k < 8 := by
      by_contra hh
      have : M.gcd x * 8 ≤ M.gcd x * k := Nat.mul_le_mul_left _ (by omega)
      omega
    have hjk : j < k := by
      have : M.gcd x * j < M.gcd x * k := by omega
      exact Nat.lt_of_mul_lt_mul_left this
    have hj0 : 0 < j := by
      rcases Nat.eq_zero_or_pos j with h | h
      · rw [h, Nat.mul_zero] at hj; omega
      · exact h
    obtain ⟨c, hc⟩ := hdvd k hkN (by omega)
    have e : 420 * j / k = c * j := by
      rw [hc, Nat.mul_assoc, Nat.mul_div_cancel_left _ (by omega)]
    refine ⟨420 * j / k, hmemV k hkN j hjk hj0, ?_⟩
    rw [e]
    rw [hc]
    generalize M.gcd x = g at hk hj
    subst hk
    rw [hj]
    ring
  -- colour the 17 values with 6 colours, each colour class pairwise good
  have hcol : ∀ v ∈ ({60, 70, 84, 105, 120, 140, 168, 180, 210, 240, 252, 280, 300, 315, 336, 350, 360} : Finset ℕ), (fun a : ℕ => if a = 60 then 1 else if a = 70 then 4 else if a = 84 then 2 else if a = 105 then 5 else if a = 120 then 2 else if a = 140 then 3 else if a = 168 then 4 else if a = 180 then 3 else if a = 210 then 0 else if a = 240 then 0 else if a = 252 then 1 else if a = 280 then 1 else if a = 300 then 4 else if a = 315 then 2 else if a = 336 then 3 else if a = 350 then 2 else if a = 360 then 5 else 0) v < 6 := by decide +kernel
  have hgood : ∀ v ∈ ({60, 70, 84, 105, 120, 140, 168, 180, 210, 240, 252, 280, 300, 315, 336, 350, 360} : Finset ℕ), ∀ w ∈ ({60, 70, 84, 105, 120, 140, 168, 180, 210, 240, 252, 280, 300, 315, 336, 350, 360} : Finset ℕ), v ≠ w → (fun a : ℕ => if a = 60 then 1 else if a = 70 then 4 else if a = 84 then 2 else if a = 105 then 5 else if a = 120 then 2 else if a = 140 then 3 else if a = 168 then 4 else if a = 180 then 3 else if a = 210 then 0 else if a = 240 then 0 else if a = 252 then 1 else if a = 280 then 1 else if a = 300 then 4 else if a = 315 then 2 else if a = 336 then 3 else if a = 350 then 2 else if a = 360 then 5 else 0) v = (fun a : ℕ => if a = 60 then 1 else if a = 70 then 4 else if a = 84 then 2 else if a = 105 then 5 else if a = 120 then 2 else if a = 140 then 3 else if a = 168 then 4 else if a = 180 then 3 else if a = 210 then 0 else if a = 240 then 0 else if a = 252 then 1 else if a = 280 then 1 else if a = 300 then 4 else if a = 315 then 2 else if a = 336 then 3 else if a = 350 then 2 else if a = 360 then 5 else 0) w →
      8 * v.gcd w ≤ v ∨ 8 * v.gcd w ≤ w := by decide +kernel
  have hmaps : ∀ x ∈ A.erase M, (fun a : ℕ => if a = 60 then 1 else if a = 70 then 4 else if a = 84 then 2 else if a = 105 then 5 else if a = 120 then 2 else if a = 140 then 3 else if a = 168 then 4 else if a = 180 then 3 else if a = 210 then 0 else if a = 240 then 0 else if a = 252 then 1 else if a = 280 then 1 else if a = 300 then 4 else if a = 315 then 2 else if a = 336 then 3 else if a = 350 then 2 else if a = 360 then 5 else 0) (420 * x / M) ∈ Finset.range 6 := by
    intro x hx
    obtain ⟨v, hv, hxv⟩ := hval x hx
    rw [Finset.mem_range, hxv, Nat.mul_div_cancel _ hMpos]
    exact hcol v hv
  have hcardE : (A.erase M).card = 7 := by rw [Finset.card_erase_of_mem hMA, hcard]
  obtain ⟨x, hx, y, hy, hxy, hc⟩ :=
    Finset.exists_ne_map_eq_of_card_lt_of_maps_to (by rw [hcardE, Finset.card_range]; omega) hmaps
  obtain ⟨v, hv, hxv⟩ := hval x hx
  obtain ⟨w, hw, hyw⟩ := hval y hy
  rw [hxv, hyw, Nat.mul_div_cancel _ hMpos, Nat.mul_div_cancel _ hMpos] at hc
  have hvw : v ≠ w := by
    rintro rfl
    exact hxy (by omega)
  have hg : v.gcd w * M = 420 * x.gcd y := by
    rw [← Nat.gcd_mul_right, ← hxv, ← hyw, Nat.gcd_mul_left]
  have hxA := (Finset.mem_erase.mp hx).2
  have hyA := (Finset.mem_erase.mp hy).2
  rcases hgood v hv w hw hvw hc with h | h
  · have h2 : 8 * (v.gcd w * M) ≤ v * M := by
      rw [← Nat.mul_assoc]; exact Nat.mul_le_mul_right M h
    exact ⟨x, hxA, y, hyA, red x y (by omega)⟩
  · have h2 : 8 * (v.gcd w * M) ≤ w * M := by
      rw [← Nat.mul_assoc]; exact Nat.mul_le_mul_right M h
    exact ⟨y, hyA, x, hxA, red y x (by rw [Nat.gcd_comm]; omega)⟩
