import Mathlib

theorem residue_integral : ∀ n i : ℕ, 1 ≤ i → i ≤ n → ∃ z : ℤ, (z : ℝ) = (∑ k ∈ Finset.Icc i n, (-(∏ t ∈ Finset.Icc 1 (n - 1), (1 - ((2 : ℝ) ^ i)⁻¹ * (2 : ℝ) ^ (t + k))) / ∏ l ∈ (Finset.Icc 1 n).erase k, (1 - (2 : ℝ) ^ ((l : ℤ) - k)))) := by
  have hQne : ∀ m : ℕ, (∏ s ∈ Finset.Icc 1 m, ((1 : ℤ) - 2 ^ s)) ≠ 0 := by
    intro m
    refine Finset.prod_ne_zero_iff.mpr (fun s hs => ?_)
    have h1 := (Finset.mem_Icc.mp hs).1
    have h2 : (2 : ℤ) ≤ 2 ^ s := by
      calc (2 : ℤ) = 2 ^ 1 := by norm_num
        _ ≤ 2 ^ s := pow_le_pow_right₀ (by norm_num) h1
    omega
  have hG : ∀ N a b : ℕ, a + b = N → ∃ z : ℤ, (∏ s ∈ Finset.Icc 1 (a + b), ((1 : ℤ) - 2 ^ s)) = z * ((∏ s ∈ Finset.Icc 1 a, ((1 : ℤ) - 2 ^ s)) * (∏ s ∈ Finset.Icc 1 b, ((1 : ℤ) - 2 ^ s))) := by
    intro N
    induction N with
    | zero =>
      intro a b h
      obtain ⟨rfl, rfl⟩ : a = 0 ∧ b = 0 := by omega
      exact ⟨1, by simp⟩
    | succ N ih =>
      intro a b h
      rcases Nat.eq_zero_or_pos a with rfl | ha
      · exact ⟨1, by simp⟩
      rcases Nat.eq_zero_or_pos b with rfl | hb
      · exact ⟨1, by simp⟩
      obtain ⟨a', rfl⟩ : ∃ a', a = a' + 1 := ⟨a - 1, by omega⟩
      obtain ⟨b', rfl⟩ : ∃ b', b = b' + 1 := ⟨b - 1, by omega⟩
      obtain ⟨z1, h1⟩ := ih a' (b' + 1) (by omega)
      obtain ⟨z2, h2⟩ := ih (a' + 1) b' (by omega)
      refine ⟨2 ^ (b' + 1) * z1 + z2, ?_⟩
      have e1 : a' + 1 + (b' + 1) = (a' + (b' + 1)) + 1 := by omega
      have e2 : a' + 1 + b' = a' + (b' + 1) := by omega
      have hA := Finset.prod_Icc_succ_top (show 1 ≤ a' + 1 by omega) (fun s => (1 : ℤ) - 2 ^ s)
      have hB := Finset.prod_Icc_succ_top (show 1 ≤ b' + 1 by omega) (fun s => (1 : ℤ) - 2 ^ s)
      have hC := Finset.prod_Icc_succ_top (show 1 ≤ a' + (b' + 1) + 1 by omega) (fun s => (1 : ℤ) - 2 ^ s)
      beta_reduce at hA hB hC
      rw [e2, hA] at h2
      rw [hB] at h1
      rw [e1, hC, hA, hB]
      linear_combination (2 ^ (b' + 1) * (1 - 2 ^ (a' + 1))) * h1 + (1 - 2 ^ (b' + 1)) * h2
  have hN : ∀ m d : ℕ, (∏ s ∈ Finset.Icc 1 d, ((1 : ℤ) - 2 ^ s)) * (∏ t ∈ Finset.Icc 1 m, ((1 : ℤ) - 2 ^ (t + d))) = ∏ s ∈ Finset.Icc 1 (d + m), ((1 : ℤ) - 2 ^ s) := by
    intro m d
    induction m with
    | zero => simp
    | succ m ih =>
      rw [Finset.prod_Icc_succ_top (by omega), show d + (m + 1) = (d + m) + 1 by omega, Finset.prod_Icc_succ_top (by omega), ← mul_assoc, ih,
        show m + 1 + d = d + m + 1 by omega]
  have hsumZ : ∀ (s : Finset ℕ) (g : ℕ → ℝ), (∀ i ∈ s, ∃ z : ℤ, (z : ℝ) = g i) → ∃ z : ℤ, (z : ℝ) = ∑ i ∈ s, g i := by
    intro s g
    induction s using Finset.induction_on with
    | empty => intro _; exact ⟨0, by simp⟩
    | insert a s ha ih =>
      intro h
      obtain ⟨za, hza⟩ := h a (Finset.mem_insert_self a s)
      obtain ⟨zs, hzs⟩ := ih (fun i hi => h i (Finset.mem_insert_of_mem hi))
      exact ⟨za + zs, by rw [Finset.sum_insert ha]; push_cast; rw [hza, hzs]⟩
  intro n i hi hin
  refine hsumZ _ _ (fun k hk => ?_)
  have hk' := Finset.mem_Icc.mp hk
  obtain ⟨d, rfl⟩ : ∃ d, k = i + d := ⟨k - i, by omega⟩
  -- numerator
  have hNr : ∏ t ∈ Finset.Icc 1 (n - 1), (1 - ((2 : ℝ) ^ i)⁻¹ * (2 : ℝ) ^ (t + (i + d))) = ((∏ t ∈ Finset.Icc 1 (n - 1), ((1 : ℤ) - 2 ^ (t + d)) : ℤ) : ℝ) := by
    push_cast
    refine Finset.prod_congr rfl (fun t _ => ?_)
    have h2i : (2 : ℝ) ^ i ≠ 0 := by positivity
    rw [show t + (i + d) = i + (t + d) by omega, pow_add, ← mul_assoc, inv_mul_cancel₀ h2i, one_mul]
  -- denominator
  have hset : (Finset.Icc 1 n).erase (i + d) = Finset.Icc 1 (i + d - 1) ∪ Finset.Icc (i + d + 1) n := by
    ext l
    simp only [Finset.mem_erase, Finset.mem_Icc, Finset.mem_union]
    omega
  have hdisj : Disjoint (Finset.Icc 1 (i + d - 1)) (Finset.Icc (i + d + 1) n) := by
    rw [Finset.disjoint_left]
    intro l h1 h2
    simp only [Finset.mem_Icc] at h1 h2
    omega
  have hD1 : (∏ l ∈ Finset.Icc 1 (i + d - 1), (1 - (2 : ℝ) ^ ((l : ℤ) - ((i + d : ℕ) : ℤ)))) * ((∏ s ∈ Finset.Icc 1 (i + d - 1), (-(2 : ℤ) ^ s) : ℤ) : ℝ) = ((∏ s ∈ Finset.Icc 1 (i + d - 1), ((1 : ℤ) - 2 ^ s) : ℤ) : ℝ) := by
    have hrefl : ∏ l ∈ Finset.Icc 1 (i + d - 1), (1 - (2 : ℝ) ^ ((l : ℤ) - ((i + d : ℕ) : ℤ))) = ∏ s ∈ Finset.Icc 1 (i + d - 1), (1 - ((2 : ℝ) ^ s)⁻¹) := by
      refine Finset.prod_nbij' (fun l => i + d - l) (fun s => i + d - s) ?_ ?_ ?_ ?_ ?_
      · intro l hl; simp only [Finset.mem_Icc] at hl ⊢; omega
      · intro l hl; simp only [Finset.mem_Icc] at hl ⊢; omega
      · intro l hl; simp only [Finset.mem_Icc] at hl; omega
      · intro l hl; simp only [Finset.mem_Icc] at hl; omega
      · intro l hl
        simp only [Finset.mem_Icc] at hl
        rw [← zpow_natCast, ← zpow_neg]
        congr 2
        push_cast [Nat.cast_sub (show l ≤ i + d by omega)]
        ring
    rw [hrefl]
    push_cast
    rw [← Finset.prod_mul_distrib]
    refine Finset.prod_congr rfl (fun s _ => ?_)
    have h2s : (2 : ℝ) ^ s ≠ 0 := by positivity
    field_simp
    ring
  have hD2 : ∏ l ∈ Finset.Icc (i + d + 1) n, (1 - (2 : ℝ) ^ ((l : ℤ) - ((i + d : ℕ) : ℤ))) = ((∏ s ∈ Finset.Icc 1 (n - (i + d)), ((1 : ℤ) - 2 ^ s) : ℤ) : ℝ) := by
    push_cast
    refine Finset.prod_nbij' (fun l => l - (i + d)) (fun s => s + (i + d)) ?_ ?_ ?_ ?_ ?_
    · intro l hl; simp only [Finset.mem_Icc] at hl ⊢; omega
    · intro l hl; simp only [Finset.mem_Icc] at hl ⊢; omega
    · intro l hl; simp only [Finset.mem_Icc] at hl; omega
    · intro l hl; simp only [Finset.mem_Icc] at hl; omega
    · intro l hl
      simp only [Finset.mem_Icc] at hl
      rw [← zpow_natCast]
      congr 2
      push_cast [Nat.cast_sub (show i + d ≤ l by omega)]
      ring
  obtain ⟨z1, hz1⟩ := hG _ d (n - 1) rfl
  obtain ⟨z2, hz2⟩ := hG _ (i + d - 1) (n - (i + d)) rfl
  rw [show i + d - 1 + (n - (i + d)) = n - 1 by omega] at hz2
  have hNZ : (∏ t ∈ Finset.Icc 1 (n - 1), ((1 : ℤ) - 2 ^ (t + d))) = z1 * z2 * ((∏ s ∈ Finset.Icc 1 (i + d - 1), ((1 : ℤ) - 2 ^ s)) * (∏ s ∈ Finset.Icc 1 (n - (i + d)), ((1 : ℤ) - 2 ^ s))) := by
    apply mul_left_cancel₀ (hQne d)
    rw [hN (n - 1) d, hz1, hz2]
    ring
  have hNZ' : ((∏ t ∈ Finset.Icc 1 (n - 1), ((1 : ℤ) - 2 ^ (t + d)) : ℤ) : ℝ) = (z1 : ℝ) * z2 * (((∏ s ∈ Finset.Icc 1 (i + d - 1), ((1 : ℤ) - 2 ^ s) : ℤ) : ℝ) * ((∏ s ∈ Finset.Icc 1 (n - (i + d)), ((1 : ℤ) - 2 ^ s) : ℤ) : ℝ)) := by
    exact_mod_cast hNZ
  have hQ1 : ((∏ s ∈ Finset.Icc 1 (i + d - 1), ((1 : ℤ) - 2 ^ s) : ℤ) : ℝ) ≠ 0 := by exact_mod_cast hQne _
  have hQ2 : ((∏ s ∈ Finset.Icc 1 (n - (i + d)), ((1 : ℤ) - 2 ^ s) : ℤ) : ℝ) ≠ 0 := by exact_mod_cast hQne _
  have hDr : (∏ l ∈ (Finset.Icc 1 n).erase (i + d), (1 - (2 : ℝ) ^ ((l : ℤ) - ((i + d : ℕ) : ℤ)))) * ((∏ s ∈ Finset.Icc 1 (i + d - 1), (-(2 : ℤ) ^ s) : ℤ) : ℝ) = ((∏ s ∈ Finset.Icc 1 (i + d - 1), ((1 : ℤ) - 2 ^ s) : ℤ) : ℝ) * ((∏ s ∈ Finset.Icc 1 (n - (i + d)), ((1 : ℤ) - 2 ^ s) : ℤ) : ℝ) := by
    rw [hset, Finset.prod_union hdisj, hD2, ← hD1]
    ring
  have hDne : (∏ l ∈ (Finset.Icc 1 n).erase (i + d), (1 - (2 : ℝ) ^ ((l : ℤ) - ((i + d : ℕ) : ℤ)))) ≠ 0 := by
    intro h0
    rw [h0, zero_mul] at hDr
    exact mul_ne_zero hQ1 hQ2 hDr.symm
  refine ⟨-(z1 * z2 * (∏ s ∈ Finset.Icc 1 (i + d - 1), (-(2 : ℤ) ^ s))), ?_⟩
  rw [hNr, eq_div_iff hDne, hNZ']
  rw [Int.cast_neg, Int.cast_mul, Int.cast_mul]
  linear_combination (-((z1 : ℝ) * z2)) * hDr
