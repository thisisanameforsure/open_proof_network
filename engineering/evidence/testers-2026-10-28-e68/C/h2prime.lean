import Mathlib

private theorem C_fac_big : ∀ N : ℕ, 4 ≤ N → 2 * N * (N + 2) < (N + 1).factorial := by
  intro N hN
  induction N, hN using Nat.le_induction with
  | base => decide
  | succ n hn ih =>
    rw [Nat.factorial_succ]
    have : 2 * (n + 1) * (n + 1 + 2) ≤ (n + 1 + 1) * (2 * n * (n + 2)) := by
      have h4 : 4 ≤ n := hn
      nlinarith [Nat.mul_le_mul h4 h4, Nat.mul_le_mul (Nat.mul_le_mul h4 h4) h4]
    calc 2 * (n + 1) * (n + 1 + 2) ≤ (n + 1 + 1) * (2 * n * (n + 2)) := this
      _ < (n + 1 + 1) * (n + 1).factorial := by
        exact Nat.mul_lt_mul_of_pos_left ih (by omega)

private theorem C_term_le (N j : ℕ) (hN : 1 ≤ N) :
    (N.factorial : ℝ) * (1 / (((j + N + 1).factorial : ℝ) - 1)) ≤
      (1 + 2 / ((N + 1).factorial : ℝ)) * (1 / ((N : ℝ) + 1)) * (1 / ((N : ℝ) + 2)) ^ j := by
  -- m! ≥ N!·(N+1)·(N+2)^j and 1/(m!-1) ≤ (1/m!)·(1 + 2/(N+1)!)
  have hm : ((N.factorial : ℝ) * ((N : ℝ) + 1) * ((N : ℝ) + 2) ^ j) ≤ ((j + N + 1).factorial : ℝ) := by
    have h := Nat.factorial_mul_pow_le_factorial (m := N + 1) (n := j)
    have he : N + 1 + j = j + N + 1 := by omega
    rw [he, Nat.factorial_succ] at h
    have h' : ((N + 1) * N.factorial * (N + 1 + 1) ^ j : ℕ) ≤ (j + N + 1).factorial := h
    have : ((N.factorial : ℝ) * ((N : ℝ) + 1) * ((N : ℝ) + 2) ^ j) =
        (((N + 1) * N.factorial * (N + 1 + 1) ^ j : ℕ) : ℝ) := by push_cast; ring
    rw [this]; exact_mod_cast h'
  have hN1 : ((N + 1).factorial : ℝ) ≤ ((j + N + 1).factorial : ℝ) := by
    exact_mod_cast Nat.factorial_le (show N + 1 ≤ j + N + 1 by omega)
  have hF1pos : (0 : ℝ) < ((N + 1).factorial : ℝ) := by exact_mod_cast Nat.factorial_pos _
  have hF1ge2 : (2 : ℝ) ≤ ((N + 1).factorial : ℝ) := by
    have : 2 ≤ (N + 1).factorial := by
      calc 2 = (2 : ℕ).factorial := rfl
        _ ≤ (N + 1).factorial := Nat.factorial_le (show 2 ≤ N + 1 by omega)
    exact_mod_cast this
  set M := ((j + N + 1).factorial : ℝ) with hM
  set A := (N.factorial : ℝ) with hA
  set P := ((N : ℝ) + 2) ^ j with hP
  have hApos : 0 < A := by rw [hA]; exact_mod_cast Nat.factorial_pos _
  have hPpos : 0 < P := by positivity
  have hMge : 2 ≤ M := le_trans hF1ge2 hN1
  -- 1/(M-1) ≤ (1 + 2/F1)/M  since  M ≤ (M-1)(1 + 2/F1)  as  M·2/F1 ≥ 2·... use M ≥ F1
  have key : 1 / (M - 1) ≤ (1 + 2 / ((N + 1).factorial : ℝ)) / M := by
    rw [div_le_div_iff₀ (by linarith) (by linarith)]
    have : (1 + 2 / ((N + 1).factorial : ℝ)) * (M - 1) - M = 2 * (M - 1) / ((N + 1).factorial : ℝ) - 1 := by
      field_simp; ring
    have h2 : 1 ≤ 2 * (M - 1) / ((N + 1).factorial : ℝ) := by
      rw [le_div_iff₀ hF1pos]; linarith
    nlinarith
  calc A * (1 / (M - 1)) ≤ A * ((1 + 2 / ((N + 1).factorial : ℝ)) / M) :=
        mul_le_mul_of_nonneg_left key hApos.le
    _ ≤ (1 + 2 / ((N + 1).factorial : ℝ)) * (1 / ((N : ℝ) + 1)) * (1 / ((N : ℝ) + 2)) ^ j := by
        rw [div_pow, one_pow]
        have hd : (0 : ℝ) < 1 + 2 / ((N + 1).factorial : ℝ) := by positivity
        rw [mul_div_assoc', div_le_iff₀ (by linarith)]
        rw [show (1 + 2 / ((N + 1).factorial : ℝ)) * (1 / ((N : ℝ) + 1)) * (1 / P) * M =
            (1 + 2 / ((N + 1).factorial : ℝ)) * (M / (((N : ℝ) + 1) * P)) by field_simp]
        rw [mul_comm A]
        apply mul_le_mul_of_nonneg_left _ hd.le
        rw [le_div_iff₀ (by positivity)]
        nlinarith [hm]

theorem tail_sharp : ∀ N : ℕ, 4 ≤ N →
    1 / ((N : ℝ) + 1) < (N.factorial : ℝ) * ∑' j : ℕ, 1 / (((j + N + 1).factorial : ℝ) - 1) ∧
    (N.factorial : ℝ) * ∑' j : ℕ, 1 / (((j + N + 1).factorial : ℝ) - 1) < 1 / N := by
  intro N hN
  have hNr : (4 : ℝ) ≤ N := by exact_mod_cast hN
  have hApos : (0 : ℝ) < N.factorial := by exact_mod_cast Nat.factorial_pos _
  have hpos : ∀ j : ℕ, 0 < ((j + N + 1).factorial : ℝ) - 1 := by
    intro j
    have : (2:ℕ) ≤ (j + N + 1).factorial := by
      calc 2 = (2 : ℕ).factorial := rfl
        _ ≤ (j + N + 1).factorial := Nat.factorial_le (by omega)
    have : (2:ℝ) ≤ ((j + N + 1).factorial : ℝ) := by exact_mod_cast this
    linarith
  set δ := (1 + 2 / ((N + 1).factorial : ℝ)) with hδ
  have hr0 : (0 : ℝ) ≤ 1 / ((N : ℝ) + 2) := by positivity
  have hr1 : 1 / ((N : ℝ) + 2) < 1 := by rw [div_lt_one (by linarith)]; linarith
  have hgeo : Summable (fun j : ℕ => δ * (1 / ((N : ℝ) + 1)) * (1 / ((N : ℝ) + 2)) ^ j) :=
    (summable_geometric_of_lt_one hr0 hr1).mul_left _
  have hle : ∀ j : ℕ, 1 / (((j + N + 1).factorial : ℝ) - 1) ≤
      (δ * (1 / ((N : ℝ) + 1)) * (1 / ((N : ℝ) + 2)) ^ j) / (N.factorial : ℝ) := by
    intro j; rw [le_div_iff₀ hApos, mul_comm]; exact C_term_le N j (by omega)
  have hs : Summable (fun j : ℕ => 1 / (((j + N + 1).factorial : ℝ) - 1)) :=
    Summable.of_nonneg_of_le (fun j => (one_div_pos.mpr (hpos j)).le) hle (hgeo.div_const _)
  constructor
  · -- lower bound: the first term alone
    have h0 : 1 / (((0 + N + 1).factorial : ℝ) - 1) ≤ ∑' j : ℕ, 1 / (((j + N + 1).factorial : ℝ) - 1) :=
      hs.le_tsum 0 (fun j _ => (one_div_pos.mpr (hpos j)).le)
    have hf : ((0 + N + 1).factorial : ℝ) = ((N : ℝ) + 1) * (N.factorial : ℝ) := by
      rw [show 0 + N + 1 = N + 1 by omega, Nat.factorial_succ]; push_cast; ring
    rw [hf] at h0
    have hlt : 1 / ((N : ℝ) + 1) < (N.factorial : ℝ) * (1 / (((N : ℝ) + 1) * (N.factorial : ℝ) - 1)) := by
      have hd : 0 < ((N : ℝ) + 1) * (N.factorial : ℝ) - 1 := by
        have := hpos 0; rw [hf] at this; exact this
      rw [mul_one_div, div_lt_div_iff₀ (by linarith) hd]
      linarith
    exact lt_of_lt_of_le hlt (mul_le_mul_of_nonneg_left h0 hApos.le)
  · have h1 := hs.tsum_le_tsum hle (hgeo.div_const _)
    rw [tsum_div_const, tsum_mul_left, tsum_geometric_of_lt_one hr0 hr1] at h1
    have hgs : (1 - 1 / ((N : ℝ) + 2))⁻¹ = ((N : ℝ) + 2) / ((N : ℝ) + 1) := by
      rw [one_sub_div (by linarith), inv_div]; ring_nf
    rw [hgs] at h1
    have hbig : (2 * N * (N + 2) : ℝ) < ((N + 1).factorial : ℝ) := by exact_mod_cast C_fac_big N hN
    have hF1pos : (0 : ℝ) < ((N + 1).factorial : ℝ) := by exact_mod_cast Nat.factorial_pos _
    have hfin : δ * (1 / ((N : ℝ) + 1)) * (((N : ℝ) + 2) / ((N : ℝ) + 1)) < 1 / N := by
      rw [hδ]
      have e : (1 + 2 / ((N + 1).factorial : ℝ)) * (1 / ((N : ℝ) + 1)) * (((N : ℝ) + 2) / ((N : ℝ) + 1))
          = (((N + 1).factorial : ℝ) + 2) * ((N : ℝ) + 2) / (((N + 1).factorial : ℝ) * ((N : ℝ) + 1) ^ 2) := by
        field_simp
      rw [e, div_lt_div_iff₀ (by positivity) (by linarith)]
      nlinarith
    calc (N.factorial : ℝ) * ∑' j : ℕ, 1 / (((j + N + 1).factorial : ℝ) - 1)
        ≤ (N.factorial : ℝ) * (δ * (1 / ((N : ℝ) + 1)) * (((N : ℝ) + 2) / ((N : ℝ) + 1)) / (N.factorial : ℝ)) :=
          mul_le_mul_of_nonneg_left h1 hApos.le
      _ = δ * (1 / ((N : ℝ) + 1)) * (((N : ℝ) + 2) / ((N : ℝ) + 1)) := by field_simp
      _ < 1 / N := hfin
