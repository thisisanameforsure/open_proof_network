import Mathlib

theorem card_n_probe :
    ∀ (A : Finset ℕ), 0 ∉ A → A.card = 12 → ∃ a ∈ A, ∃ b ∈ A, a.gcd b ≤ (a / A.card : ℚ) := by
  intro A h0 hcard
  -- the rational inequality is 12 * gcd a b ≤ a
  have red : ∀ a b : ℕ, 12 * a.gcd b ≤ a → (a.gcd b : ℚ) ≤ (a / A.card : ℚ) := by
    intro a b h
    rw [hcard, le_div_iff₀ (by norm_num)]
    exact_mod_cast (by omega : a.gcd b * 12 ≤ a)
  have hne : A.Nonempty := Finset.card_pos.mp (by omega)
  obtain ⟨M, hMA, hMmax⟩ : ∃ M ∈ A, ∀ x ∈ A, x ≤ M :=
    ⟨A.max' hne, A.max'_mem hne, fun x hx => A.le_max' x hx⟩
  have hMpos : 0 < M := Nat.pos_of_ne_zero (by rintro rfl; exact h0 hMA)
  by_cases hsmall : ∃ x ∈ A, 12 * M.gcd x ≤ M
  · obtain ⟨x, hx, h⟩ := hsmall
    exact ⟨M, hMA, x, hx, red M x h⟩
  push Not at hsmall
  -- every other element x has 27720 * x = v * M for one of the 41 values v = 27720 * j / k
  have hval : ∀ x ∈ A.erase M, ∃ v ∈ ({2520, 2772, 3080, 3465, 3960, 4620, 5040, 5544, 6160, 6930, 7560, 7920, 8316, 9240, 10080, 10395, 11088, 11880, 12320, 12600, 13860, 15120, 15400, 15840, 16632, 17325, 17640, 18480, 19404, 19800, 20160, 20790, 21560, 22176, 22680, 23100, 23760, 24255, 24640, 24948, 25200} : Finset ℕ), 27720 * x = v * M := by
    intro x hx
    obtain ⟨hxM, hxA⟩ := Finset.mem_erase.mp hx
    have hxpos : 0 < x := Nat.pos_of_ne_zero (by rintro rfl; exact h0 hxA)
    have hlt : x < M := lt_of_le_of_ne (hMmax x hxA) hxM
    have hbig : M < 12 * M.gcd x := hsmall x hxA
    obtain ⟨k, hk⟩ := Nat.gcd_dvd_left M x
    obtain ⟨j, hj⟩ := Nat.gcd_dvd_right M x
    have hkN : k < 12 := by
      by_contra hh
      have : M.gcd x * 12 ≤ M.gcd x * k := Nat.mul_le_mul_left _ (by omega)
      omega
    have hjk : j < k := by
      have : M.gcd x * j < M.gcd x * k := by omega
      exact Nat.lt_of_mul_lt_mul_left this
    have hj0 : 0 < j := by
      rcases Nat.eq_zero_or_pos j with h | h
      · rw [h, Nat.mul_zero] at hj; omega
      · exact h
    refine ⟨27720 * j / k, ?_, ?_⟩
    · interval_cases k <;> interval_cases j <;> decide +kernel
    · interval_cases k <;> interval_cases j <;> omega
  -- colour the 41 values with 10 colours, each colour class pairwise good
  have hcol : ∀ v ∈ ({2520, 2772, 3080, 3465, 3960, 4620, 5040, 5544, 6160, 6930, 7560, 7920, 8316, 9240, 10080, 10395, 11088, 11880, 12320, 12600, 13860, 15120, 15400, 15840, 16632, 17325, 17640, 18480, 19404, 19800, 20160, 20790, 21560, 22176, 22680, 23100, 23760, 24255, 24640, 24948, 25200} : Finset ℕ), (fun a : ℕ => if a = 2520 then 2 else if a = 2772 then 7 else if a = 3080 then 6 else if a = 3465 then 9 else if a = 3960 then 8 else if a = 4620 then 5 else if a = 5040 then 6 else if a = 5544 then 4 else if a = 6160 then 7 else if a = 6930 then 3 else if a = 7560 then 5 else if a = 7920 then 5 else if a = 8316 then 2 else if a = 9240 then 1 else if a = 10080 then 1 else if a = 10395 then 6 else if a = 11088 then 8 else if a = 11880 then 7 else if a = 12320 then 3 else if a = 12600 then 3 else if a = 13860 then 0 else if a = 15120 then 0 else if a = 15400 then 4 else if a = 15840 then 4 else if a = 16632 then 3 else if a = 17325 then 1 else if a = 17640 then 4 else if a = 18480 then 2 else if a = 19404 then 1 else if a = 19800 then 2 else if a = 20160 then 7 else if a = 20790 then 4 else if a = 21560 then 5 else if a = 22176 then 5 else if a = 22680 then 8 else if a = 23100 then 6 else if a = 23760 then 1 else if a = 24255 then 2 else if a = 24640 then 0 else if a = 24948 then 6 else if a = 25200 then 9 else 0) v < 10 := by decide +kernel
  have hgood : ∀ v ∈ ({2520, 2772, 3080, 3465, 3960, 4620, 5040, 5544, 6160, 6930, 7560, 7920, 8316, 9240, 10080, 10395, 11088, 11880, 12320, 12600, 13860, 15120, 15400, 15840, 16632, 17325, 17640, 18480, 19404, 19800, 20160, 20790, 21560, 22176, 22680, 23100, 23760, 24255, 24640, 24948, 25200} : Finset ℕ), ∀ w ∈ ({2520, 2772, 3080, 3465, 3960, 4620, 5040, 5544, 6160, 6930, 7560, 7920, 8316, 9240, 10080, 10395, 11088, 11880, 12320, 12600, 13860, 15120, 15400, 15840, 16632, 17325, 17640, 18480, 19404, 19800, 20160, 20790, 21560, 22176, 22680, 23100, 23760, 24255, 24640, 24948, 25200} : Finset ℕ), v ≠ w → (fun a : ℕ => if a = 2520 then 2 else if a = 2772 then 7 else if a = 3080 then 6 else if a = 3465 then 9 else if a = 3960 then 8 else if a = 4620 then 5 else if a = 5040 then 6 else if a = 5544 then 4 else if a = 6160 then 7 else if a = 6930 then 3 else if a = 7560 then 5 else if a = 7920 then 5 else if a = 8316 then 2 else if a = 9240 then 1 else if a = 10080 then 1 else if a = 10395 then 6 else if a = 11088 then 8 else if a = 11880 then 7 else if a = 12320 then 3 else if a = 12600 then 3 else if a = 13860 then 0 else if a = 15120 then 0 else if a = 15400 then 4 else if a = 15840 then 4 else if a = 16632 then 3 else if a = 17325 then 1 else if a = 17640 then 4 else if a = 18480 then 2 else if a = 19404 then 1 else if a = 19800 then 2 else if a = 20160 then 7 else if a = 20790 then 4 else if a = 21560 then 5 else if a = 22176 then 5 else if a = 22680 then 8 else if a = 23100 then 6 else if a = 23760 then 1 else if a = 24255 then 2 else if a = 24640 then 0 else if a = 24948 then 6 else if a = 25200 then 9 else 0) v = (fun a : ℕ => if a = 2520 then 2 else if a = 2772 then 7 else if a = 3080 then 6 else if a = 3465 then 9 else if a = 3960 then 8 else if a = 4620 then 5 else if a = 5040 then 6 else if a = 5544 then 4 else if a = 6160 then 7 else if a = 6930 then 3 else if a = 7560 then 5 else if a = 7920 then 5 else if a = 8316 then 2 else if a = 9240 then 1 else if a = 10080 then 1 else if a = 10395 then 6 else if a = 11088 then 8 else if a = 11880 then 7 else if a = 12320 then 3 else if a = 12600 then 3 else if a = 13860 then 0 else if a = 15120 then 0 else if a = 15400 then 4 else if a = 15840 then 4 else if a = 16632 then 3 else if a = 17325 then 1 else if a = 17640 then 4 else if a = 18480 then 2 else if a = 19404 then 1 else if a = 19800 then 2 else if a = 20160 then 7 else if a = 20790 then 4 else if a = 21560 then 5 else if a = 22176 then 5 else if a = 22680 then 8 else if a = 23100 then 6 else if a = 23760 then 1 else if a = 24255 then 2 else if a = 24640 then 0 else if a = 24948 then 6 else if a = 25200 then 9 else 0) w →
      12 * v.gcd w ≤ v ∨ 12 * v.gcd w ≤ w := by decide +kernel
  have hmaps : ∀ x ∈ A.erase M, (fun a : ℕ => if a = 2520 then 2 else if a = 2772 then 7 else if a = 3080 then 6 else if a = 3465 then 9 else if a = 3960 then 8 else if a = 4620 then 5 else if a = 5040 then 6 else if a = 5544 then 4 else if a = 6160 then 7 else if a = 6930 then 3 else if a = 7560 then 5 else if a = 7920 then 5 else if a = 8316 then 2 else if a = 9240 then 1 else if a = 10080 then 1 else if a = 10395 then 6 else if a = 11088 then 8 else if a = 11880 then 7 else if a = 12320 then 3 else if a = 12600 then 3 else if a = 13860 then 0 else if a = 15120 then 0 else if a = 15400 then 4 else if a = 15840 then 4 else if a = 16632 then 3 else if a = 17325 then 1 else if a = 17640 then 4 else if a = 18480 then 2 else if a = 19404 then 1 else if a = 19800 then 2 else if a = 20160 then 7 else if a = 20790 then 4 else if a = 21560 then 5 else if a = 22176 then 5 else if a = 22680 then 8 else if a = 23100 then 6 else if a = 23760 then 1 else if a = 24255 then 2 else if a = 24640 then 0 else if a = 24948 then 6 else if a = 25200 then 9 else 0) (27720 * x / M) ∈ Finset.range 10 := by
    intro x hx
    obtain ⟨v, hv, hxv⟩ := hval x hx
    rw [Finset.mem_range, hxv, Nat.mul_div_cancel _ hMpos]
    exact hcol v hv
  have hcardE : (A.erase M).card = 11 := by rw [Finset.card_erase_of_mem hMA, hcard]
  obtain ⟨x, hx, y, hy, hxy, hc⟩ :=
    Finset.exists_ne_map_eq_of_card_lt_of_maps_to (by rw [hcardE, Finset.card_range]; omega) hmaps
  obtain ⟨v, hv, hxv⟩ := hval x hx
  obtain ⟨w, hw, hyw⟩ := hval y hy
  rw [hxv, hyw, Nat.mul_div_cancel _ hMpos, Nat.mul_div_cancel _ hMpos] at hc
  have hvw : v ≠ w := by
    rintro rfl
    exact hxy (by omega)
  have hg : v.gcd w * M = 27720 * x.gcd y := by
    rw [← Nat.gcd_mul_right, ← hxv, ← hyw, Nat.gcd_mul_left]
  have hxA := (Finset.mem_erase.mp hx).2
  have hyA := (Finset.mem_erase.mp hy).2
  rcases hgood v hv w hw hvw hc with h | h
  · have h2 : 12 * (v.gcd w * M) ≤ v * M := by
      rw [← Nat.mul_assoc]; exact Nat.mul_le_mul_right M h
    exact ⟨x, hxA, y, hyA, red x y (by omega)⟩
  · have h2 : 12 * (v.gcd w * M) ≤ w * M := by
      rw [← Nat.mul_assoc]; exact Nat.mul_le_mul_right M h
    exact ⟨y, hyA, x, hxA, red y x (by rw [Nat.gcd_comm]; omega)⟩
