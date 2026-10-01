import sys
E = "/home/user/open_proof_network/engineering/evidence/testers-2026-09-29"
t = open(f"{E}/1050-A/h4-Proof.lean", encoding="utf-8").read()
a = t.index("  have h4_one :")
b = t.index("  clear h4_series nd_bound ineq_pow")
t = t[:a] + t[b:]
a = t.index("  open Polynomial in\n  have T_facts :")
tail = '''  have T_facts : Summable (fun m : ℕ => (1 : ℝ) / (2 ^ (m + 3) - 3)) ∧
      0 < ∑' m : ℕ, (1 : ℝ) / (2 ^ (m + 3) - 3) ∧ ∑' m : ℕ, (1 : ℝ) / (2 ^ (m + 3) - 3) ≤ 2 / 5 := by
    have h5 : ∀ m : ℕ, 5 * (2 : ℝ) ^ m ≤ 2 ^ (m + 3) - 3 := by
      intro m
      have h1 : (1 : ℝ) ≤ 2 ^ m := one_le_pow₀ (by norm_num)
      have e : (2 : ℝ) ^ (m + 3) = 8 * 2 ^ m := by rw [pow_add]; norm_num; ring
      rw [e]; linarith
    have hpos : ∀ m : ℕ, 0 < (2 : ℝ) ^ (m + 3) - 3 := fun m => by
      have := h5 m; have : (0 : ℝ) < 2 ^ m := by positivity
      linarith
    have hle : ∀ m : ℕ, (1 : ℝ) / (2 ^ (m + 3) - 3) ≤ (1 / 5) * (1 / 2) ^ m := by
      intro m
      have e : (1 / 5 : ℝ) * (1 / 2) ^ m = 1 / (5 * 2 ^ m) := by
        rw [one_div_pow]; field_simp
      rw [e]
      exact one_div_le_one_div_of_le (by positivity) (h5 m)
    have hs : Summable (fun m : ℕ => (1 : ℝ) / (2 ^ (m + 3) - 3)) :=
      Summable.of_nonneg_of_le (fun m => le_of_lt (one_div_pos.mpr (hpos m))) hle
        (summable_geometric_two.mul_left (1 / 5))
    refine ⟨hs, ?_, ?_⟩
    · exact hs.tsum_pos (fun m => le_of_lt (one_div_pos.mpr (hpos m))) 0 (one_div_pos.mpr (hpos 0))
    · calc ∑' m : ℕ, (1 : ℝ) / (2 ^ (m + 3) - 3) ≤ ∑' m : ℕ, (1 / 5 : ℝ) * (1 / 2) ^ m :=
            hs.tsum_le_tsum hle (summable_geometric_two.mul_left (1 / 5))
        _ = 2 / 5 := by rw [tsum_mul_left, tsum_geometric_two]; norm_num
  obtain ⟨_, hTpos, hTle⟩ := T_facts
  intro Qc hQc Qx hQx Aq hAq _ n
  match n with
  | 0 =>
    have hQx0 : Qx 0 = 1 := by rw [hQx, hQc]; simp
    have hAq0 : Aq 0 = 0 := by rw [hAq]; simp
    rw [hQx0, hAq0]
    push_cast
    set T := ∑' m : ℕ, (1 : ℝ) / (2 ^ (m + 3) - 3) with hT
    refine ⟨by linarith, ?_⟩
    have e : ((1 : ℝ) * (3 * T) - 0) ^ 2 * (2 : ℝ) ^ (4 * 0 * 0) = 9 * (T * T) := by ring
    rw [e]
    norm_num
    nlinarith
  | 1 =>
    -- Qx 1 = 3 - 3/2 = 3/2 and Aq 1 = 3 * (3/2) + (3/2) * (3/(2-3)) = 0, so the remainder is (9/2) T.
    have hQx1 : Qx 1 = 3 / 2 := by
      rw [hQx, hQc]; norm_num [Finset.sum_range_succ, Finset.prod_range_succ]
    have hAq1 : Aq 1 = 0 := by
      rw [hAq]; simp only [hQx1]; rw [hQc]
      norm_num [Finset.sum_range_succ, Finset.prod_range_succ]
    rw [hQx1, hAq1]
    push_cast
    set T := ∑' m : ℕ, (1 : ℝ) / (2 ^ (m + 3) - 3) with hT
    refine ⟨by nlinarith, ?_⟩
    norm_num
    nlinarith
  | n + 2 => exact h4_big Qc hQc Qx hQx Aq hAq (n + 2) (by omega)
'''
t = t[:a] + tail
open(sys.argv[1], "w", encoding="utf-8").write(t)
print(t.count("\n"))
