import Mathlib

/-- The gap lemma (node spec-ddd99827, proved on this target; a hole's child cannot declare it as a
dependency, so its proof is carried here as a private helper). -/
private theorem gap_lemma (n : ℕ) (hn : 1 ≤ n) :
    ∑' k : ℕ, (1 : ℝ) / (2 ^ (n + 1 + k) - 1) < 1 / (2 ^ n - 1) := by
  have h2n : (2 : ℝ) ≤ 2 ^ n := by
    calc (2 : ℝ) = 2 ^ 1 := by norm_num
      _ ≤ 2 ^ n := pow_le_pow_right₀ (by norm_num) hn
  have hpos1 : (0 : ℝ) < 2 ^ (n + 1) - 1 := by
    rw [pow_succ]; linarith
  have hterm : ∀ k : ℕ, (1 : ℝ) / (2 ^ (n + 1 + k) - 1) ≤ (1 / (2 ^ (n + 1) - 1)) * (1 / 2) ^ k := by
    intro k
    have h2k : (1 : ℝ) ≤ 2 ^ k := one_le_pow₀ (by norm_num)
    have hpow : (2 : ℝ) ^ (n + 1 + k) = 2 ^ (n + 1) * 2 ^ k := by rw [pow_add]
    have hposk : (0 : ℝ) < 2 ^ (n + 1 + k) - 1 := by
      rw [hpow]; nlinarith
    rw [one_div_pow, div_mul_div_comm, one_mul, div_le_div_iff₀ hposk (by positivity), hpow]
    nlinarith
  have hnonneg : ∀ k : ℕ, (0 : ℝ) ≤ 1 / (2 ^ (n + 1 + k) - 1) := by
    intro k
    have h2k : (1 : ℝ) ≤ 2 ^ k := one_le_pow₀ (by norm_num)
    have hpow : (2 : ℝ) ^ (n + 1 + k) = 2 ^ (n + 1) * 2 ^ k := by rw [pow_add]
    have hposk : (0 : ℝ) < 2 ^ (n + 1 + k) - 1 := by
      rw [hpow]; nlinarith
    exact div_nonneg zero_le_one hposk.le
  have hsum : Summable (fun k : ℕ => (1 / ((2 : ℝ) ^ (n + 1) - 1)) * (1 / 2) ^ k) :=
    (summable_geometric_of_lt_one (by norm_num) (by norm_num)).mul_left _
  have hle : ∑' k : ℕ, (1 : ℝ) / (2 ^ (n + 1 + k) - 1)
      ≤ ∑' k : ℕ, (1 / ((2 : ℝ) ^ (n + 1) - 1)) * (1 / 2) ^ k :=
    Summable.tsum_le_tsum hterm (Summable.of_nonneg_of_le hnonneg hterm hsum) hsum
  have hgeom : ∑' k : ℕ, (1 / ((2 : ℝ) ^ (n + 1) - 1)) * (1 / 2) ^ k = 2 / (2 ^ (n + 1) - 1) := by
    rw [tsum_mul_left, tsum_geometric_two]
    ring
  calc ∑' k : ℕ, (1 : ℝ) / (2 ^ (n + 1 + k) - 1) ≤ 2 / (2 ^ (n + 1) - 1) := hgeom ▸ hle
    _ < 1 / (2 ^ n - 1) := by
      rw [div_lt_div_iff₀ hpos1 (by linarith), pow_succ]
      linarith

/-- Every term is nonnegative (the term at 0 is Lean's junk value 0). -/
private theorem term_nonneg (m : ℕ) : (0 : ℝ) ≤ 1 / (2 ^ m - 1) := by
  have : (1 : ℝ) ≤ 2 ^ m := one_le_pow₀ (by norm_num)
  exact div_nonneg zero_le_one (by linarith)

/-- Every term is at most `2 (1/2)^m`, so the series is summable. -/
private theorem term_le (m : ℕ) : (1 : ℝ) / (2 ^ m - 1) ≤ 2 * (1 / 2) ^ m := by
  rcases Nat.eq_zero_or_pos m with hm | hm
  · subst hm; norm_num
  · have h2 : (2 : ℝ) ≤ 2 ^ m := by
      calc (2 : ℝ) = 2 ^ 1 := by norm_num
        _ ≤ 2 ^ m := pow_le_pow_right₀ (by norm_num) hm
    have hpos : (0 : ℝ) < 2 ^ m - 1 := by linarith
    rw [one_div_pow, div_le_iff₀ hpos]
    have : (2 : ℝ) * (1 / 2 ^ m) * (2 ^ m - 1) = 2 - 2 / 2 ^ m := by
      field_simp
    rw [this]
    have : (2 : ℝ) / 2 ^ m ≤ 1 := by
      rw [div_le_one (by positivity)]; linarith
    linarith

private theorem term_summable : Summable (fun m : ℕ => (1 : ℝ) / (2 ^ m - 1)) :=
  Summable.of_nonneg_of_le term_nonneg term_le
    ((summable_geometric_of_lt_one (by norm_num) (by norm_num)).mul_left 2)

theorem h_greedy_proof : ∀ (r : ℚ) (A : Set ℕ), 0 ∉ A →
      ∑' n : A, (1 : ℝ) / (2 ^ n.1 - 1) = r →
      ∀ n : ℕ, 1 ≤ n → (n ∈ A ↔
        (1 : ℝ) / (2 ^ n - 1) ≤ r - ∑' a : ↥(A ∩ Set.Iio n), (1 : ℝ) / (2 ^ a.1 - 1)) := by
  intro r A hA0 hr n hn
  set t : ℕ → ℝ := fun m => (1 : ℝ) / (2 ^ m - 1) with ht_def
  set f : ℕ → ℝ := A.indicator t with hf_def
  have hf : Summable f := term_summable.indicator A
  -- the whole sum, as a sum over ℕ
  have e1 : ∑' a : A, (1 : ℝ) / (2 ^ a.1 - 1) = ∑' i, f i := tsum_subtype A t
  -- the partial sum below n, as a finite sum over ℕ
  have e2 : ∑' a : ↥(A ∩ Set.Iio n), (1 : ℝ) / (2 ^ a.1 - 1) = ∑ i ∈ Finset.range n, f i := by
    rw [show ∑' a : ↥(A ∩ Set.Iio n), (1 : ℝ) / (2 ^ a.1 - 1)
          = ∑' i, (A ∩ Set.Iio n).indicator t i from tsum_subtype (A ∩ Set.Iio n) t]
    rw [tsum_eq_sum (s := Finset.range n)]
    · apply Finset.sum_congr rfl
      intro i hi
      have hi' : i ∈ Set.Iio n := Finset.mem_range.mp hi
      rw [hf_def]
      by_cases hiA : i ∈ A
      · rw [Set.indicator_of_mem (Set.mem_inter hiA hi'), Set.indicator_of_mem hiA]
      · rw [Set.indicator_of_notMem (fun h => hiA h.1), Set.indicator_of_notMem hiA]
    · intro i hi
      have hi' : i ∉ Set.Iio n := fun h => hi (Finset.mem_range.mpr h)
      exact Set.indicator_of_notMem (fun h => hi' h.2) _
  -- the remainder is the tail from n
  have e3 : (r : ℝ) - ∑' a : ↥(A ∩ Set.Iio n), (1 : ℝ) / (2 ^ a.1 - 1) = ∑' i, f (i + n) := by
    rw [e2, ← hr, e1, ← hf.sum_add_tsum_nat_add n]
    ring
  have e4 : ∑' i, f (i + n) = f n + ∑' i, f (i + n + 1) := by
    rw [((summable_nat_add_iff n).mpr hf).tsum_eq_zero_add]
    simp only [zero_add]
    congr 1
    apply tsum_congr
    intro i
    congr 1
    ring
  have htail_nonneg : (0 : ℝ) ≤ ∑' i, f (i + n + 1) :=
    tsum_nonneg (fun i => Set.indicator_nonneg (fun m _ => term_nonneg m) _)
  rw [e3, e4]
  constructor
  · intro hnA
    have : f n = t n := Set.indicator_of_mem hnA t
    rw [this]
    linarith
  · intro hle
    by_contra hnA
    have hfn : f n = 0 := Set.indicator_of_notMem hnA t
    rw [hfn, zero_add] at hle
    have hle2 : ∑' i, f (i + n + 1) ≤ ∑' k, (1 : ℝ) / (2 ^ (n + 1 + k) - 1) := by
      refine Summable.tsum_le_tsum ?_ ((summable_nat_add_iff (n + 1)).mpr hf |>.congr ?_) ?_
      · intro i
        rw [show i + n + 1 = n + 1 + i by ring]
        exact Set.indicator_le_self' (fun m _ => term_nonneg m) _
      · intro i; rfl
      · exact ((summable_nat_add_iff (n + 1)).mpr term_summable).congr
          (fun k => by rw [Nat.add_comm k (n + 1)])
    have := gap_lemma n hn
    linarith
