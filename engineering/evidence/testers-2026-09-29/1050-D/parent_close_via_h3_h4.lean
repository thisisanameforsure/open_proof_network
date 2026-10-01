import Mathlib
import Nodes.«erdos-1050--h1-v2».Context

/-! Hole `borwein` of a merged partial proof, as a node (D-12 #5, D-29).
Revised statement (D-8): the parent assembly's own `have borwein` type, with the binder types and
the real-number ascriptions the gate-written statement had dropped. -/

theorem erdos_1050__h1 : ∃ a b : ℕ → ℤ,
    (∀ n : ℕ, (b n : ℝ) * (∑' n : ℕ, (1 : ℝ) / ((2 : ℝ) ^ (n + 3) - 3)) - a n ≠ 0) ∧
    Filter.Tendsto
      (fun n : ℕ => (b n : ℝ) * (∑' n : ℕ, (1 : ℝ) / ((2 : ℝ) ^ (n + 3) - 3)) - a n)
      Filter.atTop (nhds 0) := by
  -- Informal account: annex f593a93a8960 (graph PR #185) on this node.
  -- Explicit q-Pade approximants (Borwein's route) for T = f(3)/3, f(x) = sum_j x/(2^j - x),
  -- evaluated at x_n = 3/2^n.  Qc n k: the Pade denominator's coefficients; Qx n = Q_n(x_n);
  -- Aq n = P_n(x_n) + Q_n(x_n) * c_n with c_n = sum_{j<n} 3/(2^(j+1) - 3).
  obtain ⟨Qc, hQc⟩ : ∃ Qc : ℕ → ℕ → ℚ, Qc = fun n k => (-1 : ℚ) ^ k * (2 : ℚ) ^ (k * (k - 1) / 2) *
      (∏ i ∈ Finset.range k, ((2 : ℚ) ^ (n - i) - 1) / ((2 : ℚ) ^ (i + 1) - 1)) *
      (∏ i ∈ Finset.range n, ((2 : ℚ) ^ (2 * n - k - i) - 1) / ((2 : ℚ) ^ (i + 1) - 1)) :=
    ⟨_, rfl⟩
  obtain ⟨Qx, hQx⟩ : ∃ Qx : ℕ → ℚ, Qx = fun n =>
      ∑ k ∈ Finset.range (n + 1), Qc n k * ((3 : ℚ) / (2 : ℚ) ^ n) ^ k := ⟨_, rfl⟩
  obtain ⟨Aq, hAq⟩ : ∃ Aq : ℕ → ℚ, Aq = fun n =>
      ∑ k ∈ Finset.range (n + 1),
          (∑ j ∈ Finset.range (k + 1), Qc n j / ((2 : ℚ) ^ (k - j) - 1)) * ((3 : ℚ) / (2 : ℚ) ^ n) ^ k +
        Qx n * ∑ j ∈ Finset.range n, (3 : ℚ) / ((2 : ℚ) ^ (j + 1) - 3) := ⟨_, rfl⟩
  -- Borwein's arithmetic estimate: a common denominator of size at most 2^(3n^2/2).
  have hden : ∀ n : ℕ, ∃ d : ℕ, 0 < d ∧ ((d : ℝ)) ^ 2 ≤ (2 : ℝ) ^ (3 * n * n) ∧
      (∃ z : ℤ, (z : ℚ) = d * Qx n) ∧ ∃ z : ℤ, (z : ℚ) = d * Aq n :=
    erdos_1050__h1_v2__h3 Qc hQc Qx hQx Aq hAq
  -- Borwein's analytic estimate: the remainder Q_n(x_n) f(x_n) - P_n(x_n) is positive and about 2^(-2n^2).
  have hrem : ∀ n : ℕ,
      0 < (Qx n : ℝ) * (3 * ∑' n : ℕ, (1 : ℝ) / ((2 : ℝ) ^ (n + 3) - 3)) - (Aq n : ℝ) ∧
      ((Qx n : ℝ) * (3 * ∑' n : ℕ, (1 : ℝ) / ((2 : ℝ) ^ (n + 3) - 3)) - (Aq n : ℝ)) ^ 2 *
        (2 : ℝ) ^ (4 * n * n) ≤ (2 : ℝ) ^ (2 * n + 4) :=
    erdos_1050__h1_v2__h4 Qc hQc Qx hQx Aq hAq hden
  choose d hd0 hdb hz using hden
  choose b hb using fun n => (hz n).1
  choose a ha using fun n => (hz n).2
  refine ⟨a, fun n => 3 * b n, ?_⟩
  have key : ∀ n : ℕ, (((3 * b n : ℤ)) : ℝ) * (∑' n : ℕ, (1 : ℝ) / ((2 : ℝ) ^ (n + 3) - 3)) - a n =
      (d n : ℝ) * ((Qx n : ℝ) * (3 * ∑' n : ℕ, (1 : ℝ) / ((2 : ℝ) ^ (n + 3) - 3)) - (Aq n : ℝ)) := by
    intro n
    have hb' : (b n : ℝ) = (d n : ℝ) * (Qx n : ℝ) := by exact_mod_cast hb n
    have ha' : (a n : ℝ) = (d n : ℝ) * (Aq n : ℝ) := by exact_mod_cast ha n
    push_cast
    rw [hb', ha']
    ring
  have pos : ∀ n : ℕ, 0 < (((3 * b n : ℤ)) : ℝ) * (∑' n : ℕ, (1 : ℝ) / ((2 : ℝ) ^ (n + 3) - 3)) - a n := by
    intro n
    rw [key n]
    exact mul_pos (by exact_mod_cast hd0 n) (hrem n).1
  refine ⟨fun n => (pos n).ne', ?_⟩
  set e : ℕ → ℝ := fun n => (((3 * b n : ℤ)) : ℝ) * (∑' n : ℕ, (1 : ℝ) / ((2 : ℝ) ^ (n + 3) - 3)) - a n
    with he
  have bound : ∀ n : ℕ, e n ^ 2 ≤ 64 * (1 / 2 : ℝ) ^ n := by
    intro n
    have h1 : e n ^ 2 * (2 : ℝ) ^ (4 * n * n) ≤ (2 : ℝ) ^ (3 * n * n) * (2 : ℝ) ^ (2 * n + 4) := by
      simp only [he]
      rw [key n, mul_pow, mul_assoc]
      exact mul_le_mul (hdb n) (hrem n).2 (by positivity) (by positivity)
    have h2 : (2 : ℝ) ^ (4 * n * n) = (2 : ℝ) ^ (n * n) * (2 : ℝ) ^ (3 * n * n) := by
      rw [← pow_add]; ring_nf
    have h3 : e n ^ 2 * (2 : ℝ) ^ (n * n) ≤ (2 : ℝ) ^ (2 * n + 4) := by
      have hp : (0 : ℝ) < (2 : ℝ) ^ (3 * n * n) := by positivity
      rw [h2] at h1
      nlinarith
    have h4 : (2 : ℝ) ^ (2 * n + 4) * 2 ^ n ≤ 64 * (2 : ℝ) ^ (n * n) := by
      have : 3 * n + 4 ≤ n * n + 6 := by nlinarith [sq_nonneg ((n : ℤ) - 2)]
      calc (2 : ℝ) ^ (2 * n + 4) * 2 ^ n = 2 ^ (3 * n + 4) := by rw [← pow_add]; ring_nf
        _ ≤ 2 ^ (n * n + 6) := pow_le_pow_right₀ (by norm_num) this
        _ = 64 * (2 : ℝ) ^ (n * n) := by rw [pow_add]; norm_num; ring
    have hpn : (0 : ℝ) < (2 : ℝ) ^ n := by positivity
    have hpnn : (0 : ℝ) < (2 : ℝ) ^ (n * n) := by positivity
    rw [one_div_pow, mul_one_div, le_div_iff₀ hpn]
    nlinarith
  have hsq : Filter.Tendsto (fun n => e n ^ 2) Filter.atTop (nhds 0) := by
    refine squeeze_zero (fun n => sq_nonneg _) bound ?_
    simpa using (tendsto_pow_atTop_nhds_zero_of_lt_one (by norm_num : (0 : ℝ) ≤ 1 / 2)
      (by norm_num)).const_mul 64
  have := hsq.sqrt
  simp only [Real.sqrt_zero] at this
  refine this.congr (fun n => ?_)
  exact Real.sqrt_sq (pos n).le
