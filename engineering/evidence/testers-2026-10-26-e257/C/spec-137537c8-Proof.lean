import Mathlib
import Nodes.«spec-137537c8».Context

private lemma lam_term_le (n : ℕ) : (1 : ℝ) / (2 ^ n - 1) ≤ 2 * (1 / 2 : ℝ) ^ n := by
  rcases Nat.eq_zero_or_pos n with rfl | hn
  · norm_num
  · have h1 : (2 : ℝ) ≤ 2 ^ n := by
      calc (2 : ℝ) = 2 ^ 1 := by norm_num
        _ ≤ 2 ^ n := pow_le_pow_right₀ (by norm_num) hn
    have hpos : (0 : ℝ) < 2 ^ n - 1 := by linarith
    rw [div_le_iff₀ hpos, one_div_pow, mul_comm]
    have h2 : (2 : ℝ) ^ n * (1 / 2 ^ n) = 1 := by field_simp
    have h3 : 0 < (1 : ℝ) / 2 ^ n := by positivity
    nlinarith

private lemma lam_term_nonneg (n : ℕ) : (0 : ℝ) ≤ 1 / (2 ^ n - 1) := by
  rcases Nat.eq_zero_or_pos n with rfl | hn
  · norm_num
  · have h1 : (1 : ℝ) ≤ 2 ^ n := one_le_pow₀ (by norm_num)
    exact div_nonneg zero_le_one (by linarith)

private lemma lam_summable : Summable (fun n : ℕ => (1 : ℝ) / (2 ^ n - 1)) :=
  Summable.of_nonneg_of_le lam_term_nonneg lam_term_le ((summable_geometric_two).mul_left 2)

/- For `n ≥ 1`, `1/(2^n - 1) = ∑_{j ≥ 1} (2^{-n})^j`: the geometric series behind the Lambert identity. -/
private lemma lam_term_eq_tsum {n : ℕ} (hn : 0 < n) :
    (1 : ℝ) / (2 ^ n - 1) = ∑' j : ℕ, ((1 / 2 : ℝ) ^ n) ^ (j + 1) := by
  have hr0 : (0 : ℝ) ≤ (1 / 2 : ℝ) ^ n := by positivity
  have hr1 : (1 / 2 : ℝ) ^ n < 1 := pow_lt_one₀ (by norm_num) (by norm_num) hn.ne'
  have h2 : (1 : ℝ) < 2 ^ n := one_lt_pow₀ (by norm_num) hn.ne'
  have h3 : (2 : ℝ) ^ n - 1 ≠ 0 := ne_of_gt (by linarith)
  have h4 : (1 : ℝ) - (1 / 2 : ℝ) ^ n ≠ 0 := ne_of_gt (by linarith)
  simp_rw [pow_succ]
  rw [tsum_mul_right, tsum_geometric_of_lt_one hr0 hr1]
  rw [one_div_pow] at h4 ⊢
  field_simp

/-- The Lambert identity for Erdős 257: for every `A ⊆ ℕ`, the sum `∑_{a ∈ A} 1/(2^a - 1)` is the
binary series `∑_{m ≥ 1} f_A(m) / 2^m` whose `m`-th coefficient `f_A(m) = #{a ∈ A : a ∣ m}` counts
the divisors of `m` that lie in `A`. It is the first line of every published irrationality
argument for this problem (Erdős 1948 with `f_ℕ = d`, Erdős 1968, Luca–Tachiya 2014,
Duverney–Tachiya 2019, Tao–Teräväinen with `f = ω`) and of the carry bookkeeping of the
greedy walk. The term at `m = 0` is `0` (the set `{a ∈ A | 0 < m ∧ a ∣ m}` is empty there), and
in Lean a `0 ∈ A` contributes `1/0 = 0` on the left and divides no `m ≥ 1` on the right, so no
hypothesis on `A` is needed. -/
theorem Opn.erdos_257_lambert_identity :
    ∀ (A : Set ℕ),
    ∑' n : A, (1 : ℝ) / (2 ^ n.1 - 1) =
      ∑' m : ℕ, (Set.ncard {a ∈ A | 0 < m ∧ a ∣ m} : ℝ) / 2 ^ m := by
  intro A
  classical
  set e : ℕ → ℝ := fun n => (1 : ℝ) / (2 ^ n - 1) with he
  set B : Set ℕ := A ∩ Set.Ioi 0 with hB
  have h0B : (0 : ℕ) ∉ B := fun h => lt_irrefl 0 h.2
  set g : ℕ × ℕ → ℝ := fun p => B.indicator (fun n => ((1 / 2 : ℝ) ^ n) ^ (p.2 + 1)) p.1 with hg
  have hg_nonneg : ∀ p, 0 ≤ g p := fun p => Set.indicator_nonneg (fun n _ => by positivity) _
  -- each row of `g` sums to the term of `e`
  have hrow : ∀ n, ∑' j, g (n, j) = B.indicator e n := by
    intro n
    by_cases hn : n ∈ B
    · have hn0 : 0 < n := hn.2
      simp only [hg, Set.indicator_of_mem hn, he]
      exact (lam_term_eq_tsum hn0).symm
    · simp only [hg, Set.indicator_of_notMem hn, tsum_zero]
  have hrow_summable : ∀ n, Summable (fun j => g (n, j)) := by
    intro n
    by_cases hn : n ∈ B
    · have hn0 : 0 < n := hn.2
      simp only [hg, Set.indicator_of_mem hn]
      have hr0 : (0 : ℝ) ≤ (1 / 2 : ℝ) ^ n := by positivity
      have hr1 : (1 / 2 : ℝ) ^ n < 1 := pow_lt_one₀ (by norm_num) (by norm_num) hn0.ne'
      exact (summable_nat_add_iff 1).mpr (summable_geometric_of_lt_one hr0 hr1)
    · simp only [hg, Set.indicator_of_notMem hn]
      exact summable_zero
  have he_summable : Summable e := lam_summable
  have hg_summable : Summable g := by
    rw [summable_prod_of_nonneg hg_nonneg]
    refine ⟨hrow_summable, ?_⟩
    simp_rw [hrow]
    exact he_summable.indicator B
  -- the left side as a sum over ℕ of the indicator of `B`
  have hL : ∑' n : A, e n = ∑' n : ℕ, B.indicator e n := by
    rw [tsum_subtype A e]
    apply tsum_congr
    intro n
    by_cases hn : n ∈ A
    · by_cases hn0 : n = 0
      · subst hn0
        rw [Set.indicator_of_notMem h0B, Set.indicator_of_mem hn]
        simp [he]
      · have hnB : n ∈ B := ⟨hn, Nat.pos_of_ne_zero hn0⟩
        rw [Set.indicator_of_mem hn, Set.indicator_of_mem hnB]
    · have hnB : n ∉ B := fun h => hn h.1
      rw [Set.indicator_of_notMem hn, Set.indicator_of_notMem hnB]
  -- the double series, summed row by row
  have hmid : ∑' n : ℕ, B.indicator e n = ∑' p : ℕ × ℕ, g p := by
    rw [hg_summable.tsum_prod]
    simp_rw [hrow]
  -- the double series, summed along the fibres of `(n, j) ↦ n * (j + 1)`
  set φ : ℕ × ℕ → ℕ := fun p => p.1 * (p.2 + 1) with hφ
  have hfib : HasSum (fun m => ∑' p : (φ ⁻¹' {m}), g p) (∑' p, g p) :=
    hg_summable.hasSum.tsum_fiberwise φ
  have hR : ∑' p : ℕ × ℕ, g p =
      ∑' m : ℕ, (Set.ncard {a ∈ A | 0 < m ∧ a ∣ m} : ℝ) / 2 ^ m := by
    rw [← hfib.tsum_eq]
    apply tsum_congr
    intro m
    rcases Nat.eq_zero_or_pos m with rfl | hm
    · -- the fibre over 0 is the row n = 0, where the indicator vanishes
      have h1 : ∀ p : (φ ⁻¹' {0}), g p = 0 := by
        rintro ⟨⟨n, j⟩, hp⟩
        have hp' : n * (j + 1) = 0 := by
          simpa [hφ] using hp
        have hn : n = 0 := (mul_eq_zero.mp hp').resolve_right (Nat.succ_ne_zero j)
        simp only [hg]
        rw [hn]
        exact Set.indicator_of_notMem h0B _
      have h2 : {a ∈ A | 0 < 0 ∧ a ∣ 0} = ∅ := by
        ext a
        simp
      rw [tsum_congr h1, tsum_zero, h2, Set.ncard_empty]
      simp
    · -- the fibre over m ≥ 1 is finite: one point per divisor of m
      set T : Finset (ℕ × ℕ) := (Nat.divisors m).image (fun d => (d, m / d - 1)) with hT
      have hsupp : ∀ p ∉ T, (φ ⁻¹' {m}).indicator g p = 0 := by
        rintro ⟨n, j⟩ hp
        by_contra hne
        apply hp
        have hmem : (n, j) ∈ φ ⁻¹' {m} := by
          by_contra h
          exact hne (Set.indicator_of_notMem h _)
        have hφm : n * (j + 1) = m := by simpa [hφ] using hmem
        rw [Set.indicator_of_mem hmem] at hne
        have hnB : n ∈ B := by
          by_contra h
          exact hne (by simp only [hg]; exact Set.indicator_of_notMem h _)
        have hn0 : 0 < n := hnB.2
        have hdiv : n ∣ m := ⟨j + 1, hφm.symm⟩
        have hj : m / n - 1 = j := by
          rw [← hφm, Nat.mul_div_cancel_left (j + 1) hn0]
          simp
        rw [hT, Finset.mem_image]
        exact ⟨n, Nat.mem_divisors.mpr ⟨hdiv, hm.ne'⟩, by rw [hj]⟩
      have hinj : Set.InjOn (fun d : ℕ => (d, m / d - 1)) ↑(Nat.divisors m) :=
        fun a _ b _ h => (Prod.mk.inj h).1
      have hS : {a ∈ A | 0 < m ∧ a ∣ m} = ↑((Nat.divisors m).filter (fun a => a ∈ A)) := by
        ext a
        simp only [Set.mem_ofPred_eq, Finset.coe_filter, Nat.mem_divisors]
        constructor
        · rintro ⟨ha, _, hd⟩
          exact ⟨⟨hd, hm.ne'⟩, ha⟩
        · rintro ⟨⟨hd, _⟩, ha⟩
          exact ⟨ha, hm, hd⟩
      rw [tsum_subtype (φ ⁻¹' {m}) g, tsum_eq_sum hsupp, hT, Finset.sum_image hinj]
      have hterm : ∀ d ∈ Nat.divisors m,
          (φ ⁻¹' {m}).indicator g (d, m / d - 1) = if d ∈ A then (1 / 2 : ℝ) ^ m else 0 := by
        intro d hd
        have hd' := Nat.mem_divisors.mp hd
        have hd0 : 0 < d := Nat.pos_of_mem_divisors hd
        have hq : 1 ≤ m / d := Nat.div_pos (Nat.le_of_dvd hm hd'.1) hd0
        have hφd : (d, m / d - 1) ∈ φ ⁻¹' {m} := by
          show d * (m / d - 1 + 1) = m
          rw [Nat.sub_add_cancel hq, Nat.mul_div_cancel' hd'.1]
        rw [Set.indicator_of_mem hφd]
        simp only [hg]
        by_cases hdA : d ∈ A
        · have hdB : d ∈ B := ⟨hdA, hd0⟩
          rw [Set.indicator_of_mem hdB, if_pos hdA, ← pow_mul, Nat.sub_add_cancel hq,
            Nat.mul_div_cancel' hd'.1]
        · have hdB : d ∉ B := fun h => hdA h.1
          rw [Set.indicator_of_notMem hdB, if_neg hdA]
      rw [Finset.sum_congr rfl hterm, ← Finset.sum_filter, Finset.sum_const, nsmul_eq_mul,
        hS, Set.ncard_coe_finset, one_div_pow]
      ring
  rw [hL, hmid, hR]
