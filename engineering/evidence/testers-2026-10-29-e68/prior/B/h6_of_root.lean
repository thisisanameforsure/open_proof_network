import Mathlib

/-! Evidence for postmortem #1158 (not a node): Irrational S → h6, given h5 (proved as #1162).
Together with #1154's assembly (h6 → Irrational S), h6 is equivalent to the root. -/

private theorem B_zero_of_growth (e : ℕ → ℝ) (M : ℕ) (hM : 1 ≤ M)
    (hrec : ∀ N, M ≤ N → e (N + 1) = ((N : ℝ) + 1) * e N)
    (hsmall : ∀ N, M ≤ N → |e N| < 1) : e M = 0 := by
  by_contra h0
  have hpos : 0 < |e M| := abs_pos.mpr h0
  have hgrow : ∀ k : ℕ, (2:ℝ) ^ k * |e M| ≤ |e (M + k)| := by
    intro k
    induction k with
    | zero => simp
    | succ k ih =>
      have := hrec (M + k) (by omega)
      rw [show M + (k + 1) = M + k + 1 by omega, this, abs_mul]
      have h1 : (1:ℝ) ≤ ((M + k : ℕ) : ℝ) := by exact_mod_cast (show 1 ≤ M + k by omega)
      have h2 : (2:ℝ) ≤ |((M + k : ℕ) : ℝ) + 1| := by
        rw [abs_of_pos (by positivity)]; linarith
      calc (2:ℝ) ^ (k + 1) * |e M| = 2 * ((2:ℝ) ^ k * |e M|) := by ring
        _ ≤ |((M + k : ℕ) : ℝ) + 1| * |e (M + k)| :=
          mul_le_mul h2 ih (by positivity) (abs_nonneg _)
  obtain ⟨k, hk⟩ := pow_unbounded_of_one_lt (1 / |e M|) (by norm_num : (1:ℝ) < 2)
  have hg := hgrow k
  have h1 : 1 ≤ (2:ℝ) ^ k * |e M| := by
    rw [div_lt_iff₀ hpos] at hk; linarith
  have hs := hsmall (M + k) (by omega)
  linarith

theorem B_h6_of_irrational
    (h5 : ∀ (N : ℕ), (4 : ℕ) ≤ N → ∃ (c : ℝ), (1 : ℝ) / ((↑N : ℝ) + (1 : ℝ)) < c ∧ c < (1 : ℝ) / (↑N : ℝ) ∧
      (↑N.factorial : ℝ) * ∑' (n : ℕ), (1 : ℝ) / ((↑(n + (2 : ℕ)).factorial : ℝ) - (1 : ℝ)) =
        ∑ n ∈ Finset.Icc (2 : ℕ) N, (↑N.factorial : ℝ) / ((↑n.factorial : ℝ) - (1 : ℝ)) + c)
    (hirr : Irrational (∑' n : ℕ, 1 / ((n + 2).factorial - 1 : ℝ))) :
    ∀ (M : ℕ), ∃ (N : ℕ), M ≤ N ∧
      (Int.fract (∑ n ∈ Finset.Icc (2 : ℕ) N, (↑N.factorial : ℝ) / ((↑n.factorial : ℝ) - (1 : ℝ))) ≤
          (1 : ℝ) - (1 : ℝ) / (↑N : ℝ) ∨
        (1 : ℝ) - (1 : ℝ) / ((↑N : ℝ) + (1 : ℝ)) ≤
          Int.fract (∑ n ∈ Finset.Icc (2 : ℕ) N, (↑N.factorial : ℝ) / ((↑n.factorial : ℝ) - (1 : ℝ)))) := by
  set S : ℝ := ∑' n : ℕ, 1 / ((n + 2).factorial - 1 : ℝ) with hSdef
  set F : ℕ → ℝ := fun N => ∑ n ∈ Finset.Icc (2 : ℕ) N, (N.factorial : ℝ) / ((n.factorial : ℝ) - 1) with hFdef
  by_contra hneg
  push_neg at hneg
  obtain ⟨M, hM⟩ := hneg
  set M' := max M 4 with hM'
  -- e N = N! S - (⌊F N⌋ + 1)
  let e : ℕ → ℝ := fun N => (N.factorial : ℝ) * S - ((⌊F N⌋ : ℝ) + 1)
  have hbound : ∀ N, M' ≤ N → |e N| < 1 / ((N : ℝ) * ((N : ℝ) + 1)) := by
    intro N hN
    obtain ⟨c, hc1, hc2, hS⟩ := h5 N (le_trans (le_max_right _ _) hN)
    obtain ⟨hf1, hf2⟩ := hM N (le_trans (le_max_left _ _) hN)
    have hNpos : (0:ℝ) < N := by exact_mod_cast (show 0 < N by omega)
    have he : e N = Int.fract (F N) + c - 1 := by
      simp only [e]
      rw [show (N.factorial : ℝ) * S = F N + c from hS, Int.fract]
      ring
    rw [he, abs_lt]
    have hid : 1 / ((N : ℝ) * ((N : ℝ) + 1)) = 1 / (N : ℝ) - 1 / ((N : ℝ) + 1) := by
      field_simp; ring
    rw [hid]
    constructor <;> linarith
  have hsmall : ∀ N, M' ≤ N → |e N| < 1 := by
    intro N hN
    have hNr : (4:ℝ) ≤ N := by exact_mod_cast (le_trans (le_max_right _ _) hN)
    have h := hbound N hN
    have : 1 / ((N : ℝ) * ((N : ℝ) + 1)) ≤ 1 := by
      rw [div_le_one (by positivity)]; nlinarith
    linarith
  have hrec : ∀ N, M' ≤ N → e (N + 1) = ((N : ℝ) + 1) * e N := by
    intro N hN
    have hNr : (4:ℝ) ≤ N := by exact_mod_cast (le_trans (le_max_right _ _) hN)
    -- d := (N+1)(⌊F N⌋+1) - (⌊F (N+1)⌋+1) is an integer equal to e (N+1) - (N+1) e N
    have hfac : ((N + 1).factorial : ℝ) = ((N : ℝ) + 1) * (N.factorial : ℝ) := by
      push_cast [Nat.factorial_succ]; ring
    set d : ℤ := ((N : ℤ) + 1) * (⌊F N⌋ + 1) - (⌊F (N + 1)⌋ + 1) with hd
    have hdeq : (d : ℝ) = e (N + 1) - ((N : ℝ) + 1) * e N := by
      simp only [e, hd, hfac]; push_cast; ring
    have h1 := hbound N hN
    have h2 := hbound (N + 1) (by omega)
    have hb : |(d : ℝ)| < 1 := by
      rw [hdeq]
      have hN0 : (0:ℝ) < N := by linarith
      have hx : |((N : ℝ) + 1) * e N| < 1 / (N : ℝ) := by
        rw [abs_mul, abs_of_pos (by positivity)]
        calc ((N : ℝ) + 1) * |e N| < ((N : ℝ) + 1) * (1 / ((N : ℝ) * ((N : ℝ) + 1))) :=
              mul_lt_mul_of_pos_left h1 (by positivity)
          _ = 1 / (N : ℝ) := by field_simp
      have hy : |e (N + 1)| < 1 / 2 := by
        have : 1 / (((N + 1 : ℕ) : ℝ) * (((N + 1 : ℕ) : ℝ) + 1)) ≤ 1 / 2 := by
          rw [div_le_div_iff₀ (by positivity) (by norm_num)]; push_cast; nlinarith
        linarith
      have : 1 / (N : ℝ) ≤ 1 / 4 := by
        rw [div_le_div_iff₀ hN0 (by norm_num)]; linarith
      calc |e (N + 1) - ((N : ℝ) + 1) * e N| ≤ |e (N + 1)| + |((N : ℝ) + 1) * e N| := abs_sub _ _
        _ < 1 := by linarith
    have hd0 : d = 0 := by
      have : |d| < 1 := by exact_mod_cast hb
      obtain ⟨h1, h2⟩ := abs_lt.mp this
      omega
    have : (d : ℝ) = 0 := by exact_mod_cast hd0
    linarith
  have hz := B_zero_of_growth e M' (by omega) hrec hsmall
  apply hirr
  refine ⟨((⌊F M'⌋ + 1 : ℤ) : ℚ) / (M'.factorial : ℚ), ?_⟩
  have hfpos : (0:ℝ) < (M'.factorial : ℝ) := by exact_mod_cast Nat.factorial_pos M'
  simp only [e] at hz
  push_cast
  field_simp
  linarith
