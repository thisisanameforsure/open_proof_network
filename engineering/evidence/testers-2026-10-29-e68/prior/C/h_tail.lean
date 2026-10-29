import Mathlib

private lemma tail_term_le (K i : ℕ) (hK : 1 ≤ K) :
    (K.factorial : ℝ) * (1 / ((i + (K - 1) + 2).factorial - 1 : ℝ)) ≤ 2 * (1 / ((K : ℝ) + 1)) ^ (i + 1) := by
  have hidx : i + (K - 1) + 2 = K + (i + 1) := by omega
  rw [hidx]
  have hfac : (K.factorial : ℝ) * ((K : ℝ) + 1) ^ (i + 1) ≤ ((K + (i + 1)).factorial : ℝ) := by
    exact_mod_cast Nat.factorial_mul_pow_le_factorial
  have hKpos : (0 : ℝ) < K.factorial := by exact_mod_cast Nat.factorial_pos K
  have hpow : (0 : ℝ) < ((K : ℝ) + 1) ^ (i + 1) := by positivity
  have hbig : (2 : ℝ) ≤ ((K + (i + 1)).factorial : ℝ) := by
    have : 2 ≤ (K + (i + 1)).factorial := by
      calc 2 = (2 : ℕ).factorial := rfl
        _ ≤ (K + (i + 1)).factorial := Nat.factorial_le (by omega)
    exact_mod_cast this
  have hden : (0 : ℝ) < ((K + (i + 1)).factorial : ℝ) - 1 := by linarith
  rw [div_pow, one_pow, mul_one_div, mul_one_div, div_le_iff₀ hden]
  rw [div_mul_eq_mul_div, le_div_iff₀ hpow]
  nlinarith

theorem tail_bound : ∀ N : ℕ, 3 ≤ N →
      0 < ((N + 2).factorial : ℝ) * ∑' i : ℕ, 1 / ((i + (N + 1) + 2).factorial - 1 : ℝ) ∧
      ((N + 2).factorial : ℝ) * ∑' i : ℕ, 1 / ((i + (N + 1) + 2).factorial - 1 : ℝ) < 1 / 2 := by
  intro N hN
  set K := N + 2 with hKdef
  have hK1 : 1 ≤ K := by omega
  have hKm : K - 1 = N + 1 := by omega
  have hKpos : (0 : ℝ) < K.factorial := by exact_mod_cast Nat.factorial_pos K
  have hr0 : (0 : ℝ) ≤ 1 / ((K : ℝ) + 1) := by positivity
  have hr1 : 1 / ((K : ℝ) + 1) < 1 := by
    rw [div_lt_one (by positivity)]; have : (1 : ℝ) ≤ K := by exact_mod_cast hK1
    linarith
  have hgeom : Summable (fun i : ℕ => 2 * (1 / ((K : ℝ) + 1)) ^ (i + 1)) :=
    ((summable_geometric_of_lt_one hr0 hr1).mul_left (1 / ((K : ℝ) + 1))).mul_left 2 |>.congr
      (fun i => by ring)
  have hterm_pos : ∀ i : ℕ, 0 < 1 / ((i + (N + 1) + 2).factorial - 1 : ℝ) := by
    intro i
    have : 2 ≤ (i + (N + 1) + 2).factorial := by
      calc 2 = (2 : ℕ).factorial := rfl
        _ ≤ (i + (N + 1) + 2).factorial := Nat.factorial_le (by omega)
    have : (2 : ℝ) ≤ ((i + (N + 1) + 2).factorial : ℝ) := by exact_mod_cast this
    apply div_pos one_pos; linarith
  have hle : ∀ i : ℕ, 1 / ((i + (N + 1) + 2).factorial - 1 : ℝ) ≤
      (2 * (1 / ((K : ℝ) + 1)) ^ (i + 1)) / K.factorial := by
    intro i
    rw [le_div_iff₀ hKpos, mul_comm]
    have := tail_term_le K i hK1
    rw [hKm] at this
    exact this
  have hsum : Summable (fun i : ℕ => 1 / ((i + (N + 1) + 2).factorial - 1 : ℝ)) :=
    Summable.of_nonneg_of_le (fun i => (hterm_pos i).le) hle (hgeom.div_const _)
  constructor
  · exact mul_pos hKpos (hsum.tsum_pos (fun i => (hterm_pos i).le) 0 (hterm_pos 0))
  · have h1 : ∑' i : ℕ, 1 / ((i + (N + 1) + 2).factorial - 1 : ℝ) ≤
        ∑' i : ℕ, (2 * (1 / ((K : ℝ) + 1)) ^ (i + 1)) / K.factorial :=
      hsum.tsum_le_tsum hle (hgeom.div_const _)
    have h2 : ∑' i : ℕ, (2 * (1 / ((K : ℝ) + 1)) ^ (i + 1)) / K.factorial = (2 / K) / K.factorial := by
      rw [tsum_div_const]
      congr 1
      have hK1' : (1 : ℝ) ≤ K := by exact_mod_cast hK1
      have hK0 : (K : ℝ) ≠ 0 := by positivity
      have : ∑' i : ℕ, 2 * (1 / ((K : ℝ) + 1)) ^ (i + 1) =
          2 * (1 / ((K : ℝ) + 1)) * ∑' i : ℕ, (1 / ((K : ℝ) + 1)) ^ i := by
        rw [← tsum_mul_left]; congr 1; ext i; ring
      rw [this, tsum_geometric_of_lt_one hr0 hr1]
      field_simp
      ring_nf
      field_simp
    have hK5 : (5 : ℝ) ≤ K := by exact_mod_cast (show 5 ≤ K by omega)
    calc ((N + 2).factorial : ℝ) * ∑' i : ℕ, 1 / ((i + (N + 1) + 2).factorial - 1 : ℝ)
        ≤ K.factorial * ((2 / K) / K.factorial) := by
          rw [← h2]; exact mul_le_mul_of_nonneg_left h1 hKpos.le
      _ = 2 / K := by field_simp
      _ < 1 / 2 := by rw [div_lt_div_iff₀ (by linarith) (by norm_num)]; linarith
