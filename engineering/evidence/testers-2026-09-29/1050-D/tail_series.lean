import Mathlib

theorem tail_series (n : ℕ) (hn : 1 ≤ n) :
    HasSum (fun k : ℕ => ((3 : ℝ) / 2 ^ n) ^ k / ((2 : ℝ) ^ k - 1))
      (3 * ∑' m : ℕ, (1 : ℝ) / ((2 : ℝ) ^ (m + 3) - 3) -
        ∑ j ∈ Finset.range n, (3 : ℝ) / ((2 : ℝ) ^ (j + 1) - 3)) := by
  have h2n : (2 : ℝ) ≤ 2 ^ n := by
    calc (2 : ℝ) = 2 ^ 1 := by norm_num
      _ ≤ 2 ^ n := pow_le_pow_right₀ (by norm_num) hn
  set x : ℝ := (3 : ℝ) / 2 ^ n with hxdef
  have hx0 : 0 < x := by positivity
  have hx2 : x < 2 := by
    rw [hxdef, div_lt_iff₀ (by positivity)]; nlinarith
  -- the double family
  set f : ℕ → ℕ → ℝ := fun j k => x ^ (k + 1) * ((1 : ℝ) / 2 ^ (j + 1)) ^ (k + 1) with hfdef
  have hf0 : ∀ j k, 0 ≤ f j k := fun j k => by positivity
  -- rows (fixed j): a geometric series
  have hrow : ∀ j : ℕ, HasSum (f j) (3 / ((2 : ℝ) ^ (j + n + 1) - 3)) := by
    intro j
    have hr0 : 0 ≤ x * (1 / 2 ^ (j + 1)) := by positivity
    have hr1 : x * (1 / 2 ^ (j + 1)) < 1 := by
      have : (2 : ℝ) ≤ 2 ^ (j + 1) := by
        calc (2 : ℝ) = 2 ^ 1 := by norm_num
          _ ≤ 2 ^ (j + 1) := pow_le_pow_right₀ (by norm_num) (by omega)
      rw [mul_one_div, div_lt_one (by positivity)]; linarith
    have h := (hasSum_geometric_of_lt_one hr0 hr1).mul_left (x * (1 / 2 ^ (j + 1)))
    have hpos : (0 : ℝ) < 2 ^ (j + n + 1) - 3 := by
      have : (4 : ℝ) ≤ 2 ^ (j + n + 1) := by
        calc (4 : ℝ) = 2 ^ 2 := by norm_num
          _ ≤ 2 ^ (j + n + 1) := pow_le_pow_right₀ (by norm_num) (by omega)
      linarith
    have e : (2 : ℝ) ^ (j + n + 1) = 2 ^ n * 2 ^ (j + 1) := by rw [← pow_add]; congr 1; omega
    have hfun : f j = fun i => x * (1 / 2 ^ (j + 1)) * (x * (1 / 2 ^ (j + 1))) ^ i := by
      funext k; simp only [hfdef]; rw [← mul_pow, pow_succ]; ring
    have hval : 3 / ((2 : ℝ) ^ (j + n + 1) - 3) = x * (1 / 2 ^ (j + 1)) * (1 - x * (1 / 2 ^ (j + 1)))⁻¹ := by
      rw [e] at hpos ⊢
      have h1 : (1 : ℝ) - x * (1 / 2 ^ (j + 1)) ≠ 0 := by linarith
      rw [hxdef] at h1 ⊢
      field_simp
    rw [hfun, hval]; exact h
  -- columns (fixed k): a geometric series in j
  have hcol : ∀ k : ℕ, HasSum (fun j => f j k) (x ^ (k + 1) / ((2 : ℝ) ^ (k + 1) - 1)) := by
    intro k
    have hq0 : (0 : ℝ) ≤ 1 / 2 ^ (k + 1) := by positivity
    have hq1 : (1 : ℝ) / 2 ^ (k + 1) < 1 := by
      rw [div_lt_one (by positivity)]; exact one_lt_pow₀ (by norm_num) (by omega)
    have h := ((hasSum_geometric_of_lt_one hq0 hq1).mul_left (1 / 2 ^ (k + 1))).mul_left (x ^ (k + 1))
    have hpos : (0 : ℝ) < 2 ^ (k + 1) - 1 := by
      have : (1 : ℝ) < 2 ^ (k + 1) := one_lt_pow₀ (by norm_num) (by omega)
      linarith
    have hfun : (fun j => f j k) = fun i => x ^ (k + 1) * (1 / 2 ^ (k + 1) * (1 / 2 ^ (k + 1)) ^ i) := by
      funext j; simp only [hfdef]
      rw [← one_div_pow, ← one_div_pow, ← pow_mul, ← pow_mul, ← pow_add]
      congr 2; ring
    have hval : x ^ (k + 1) / ((2 : ℝ) ^ (k + 1) - 1) =
        x ^ (k + 1) * (1 / 2 ^ (k + 1) * (1 - 1 / 2 ^ (k + 1))⁻¹) := by
      have h1 : (1 : ℝ) - 1 / 2 ^ (k + 1) ≠ 0 := by linarith
      field_simp
    rw [hfun, hval]; exact h
  -- the double sum, both ways
  have hsum2' : Summable (fun p : ℕ × ℕ => f p.1 p.2) := by
    rw [summable_prod_of_nonneg (fun p => hf0 p.1 p.2)]
    refine ⟨fun j => (hrow j).summable, ?_⟩
    have hts : (fun j => ∑' k, f j k) = fun j => 3 / ((2 : ℝ) ^ (j + n + 1) - 3) :=
      funext fun j => (hrow j).tsum_eq
    show Summable (fun j => ∑' k, f j k)
    rw [hts]
    refine Summable.of_nonneg_of_le (fun j => ?_) (fun j => ?_) (summable_geometric_two.mul_left 3)
    · have : (4 : ℝ) ≤ 2 ^ (j + n + 1) := by
        calc (4 : ℝ) = 2 ^ 2 := by norm_num
          _ ≤ 2 ^ (j + n + 1) := pow_le_pow_right₀ (by norm_num) (by omega)
      exact div_nonneg (by norm_num) (by linarith)
    · have hj : (1 : ℝ) ≤ 2 ^ j := one_le_pow₀ (by norm_num)
      have e : (2 : ℝ) ^ (j + n + 1) = 2 ^ j * 2 ^ (n + 1) := by rw [← pow_add]; ring_nf
      have h4 : (4 : ℝ) ≤ 2 ^ (n + 1) := by
        calc (4 : ℝ) = 2 ^ 2 := by norm_num
          _ ≤ 2 ^ (n + 1) := pow_le_pow_right₀ (by norm_num) (by omega)
      have hp : (0 : ℝ) < 2 ^ (j + n + 1) - 3 := by rw [e]; nlinarith
      rw [div_le_iff₀ hp, one_div_pow, e]
      have hh : (1 / 2 : ℝ) ^ j * 2 ^ j = 1 := by rw [← mul_pow]; norm_num
      rw [one_div_pow] at hh
      field_simp
      nlinarith
  have hsum2 : Summable (Function.uncurry f) := hsum2'
  have hS := hsum2.hasSum
  have hA := hS.prod_fiberwise (fun j => hrow j)
  have hB := ((Equiv.prodComm ℕ ℕ).hasSum_iff.mpr hS).prod_fiberwise (fun k => hcol k)
  -- the row sums are the tail of 3T
  have hg : Summable (fun j : ℕ => (3 : ℝ) / ((2 : ℝ) ^ (j + 1) - 3)) :=
    (summable_nat_add_iff n).mp hA.summable
  have hsplit_n := hg.sum_add_tsum_nat_add n
  have hsplit_2 := hg.sum_add_tsum_nat_add 2
  have h01 : ∑ i ∈ Finset.range 2, (3 : ℝ) / ((2 : ℝ) ^ (i + 1) - 3) = 0 := by
    norm_num [Finset.sum_range_succ]
  have h3T : ∑' i : ℕ, (3 : ℝ) / ((2 : ℝ) ^ (i + 2 + 1) - 3) =
      3 * ∑' m : ℕ, (1 : ℝ) / ((2 : ℝ) ^ (m + 3) - 3) := by
    rw [← tsum_mul_left]
    congr 1; funext i
    rw [show i + 2 + 1 = i + 3 by ring]; ring
  have hval : ∑' p, Function.uncurry f p = 3 * ∑' m : ℕ, (1 : ℝ) / ((2 : ℝ) ^ (m + 3) - 3) -
      ∑ j ∈ Finset.range n, (3 : ℝ) / ((2 : ℝ) ^ (j + 1) - 3) := by
    rw [← hA.tsum_eq]
    rw [h01, zero_add, h3T] at hsplit_2
    linarith
  have h0 : ∑ i ∈ Finset.range 1, x ^ i / ((2 : ℝ) ^ i - 1) = 0 := by simp
  rw [← hval]
  refine (hasSum_nat_add_iff' 1).mp ?_
  rw [h0, sub_zero]
  exact hB
