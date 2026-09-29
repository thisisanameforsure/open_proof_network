import Mathlib

theorem tail3 (n : ℕ) (hn : 1 ≤ n) :
    ∑' m : ℕ, (3 : ℝ) / (2 ^ (m + n + 1) - 3) = ∑' s : ℕ, ((3 : ℝ) / 2 ^ n) ^ (s + 1) / (2 ^ (s + 1) - 1) := by
  set f : ℕ → ℕ → ℝ := fun m s => ((3 : ℝ) / 2 ^ (n + 1)) ^ (s + 1) * ((1 : ℝ) / 2 ^ (s + 1)) ^ m with hf
  have key : ∀ m s, f m s = ((3 : ℝ) / 2 ^ (m + n + 1)) ^ (s + 1) := by
    intro m s
    simp only [hf]
    rw [div_pow, div_pow, div_pow, one_pow, ← pow_mul, ← pow_mul, ← pow_mul,
      show (m + n + 1) * (s + 1) = (n + 1) * (s + 1) + (s + 1) * m by ring, pow_add]
    field_simp
    exact pow_add _ _ _
  have hpos : ∀ m s, 0 ≤ f m s := fun m s => by rw [key]; positivity
  have h4 : ∀ m : ℕ, (4 : ℝ) ≤ 2 ^ (m + n + 1) := by
    intro m
    calc (4 : ℝ) = 2 ^ 2 := by norm_num
      _ ≤ 2 ^ (m + n + 1) := pow_le_pow_right₀ (by norm_num) (by omega)
  have inner1 : ∀ m, HasSum (f m) ((3 : ℝ) / (2 ^ (m + n + 1) - 3)) := by
    intro m
    have hr0 : 0 ≤ (3 : ℝ) / 2 ^ (m + n + 1) := by positivity
    have hr1 : (3 : ℝ) / 2 ^ (m + n + 1) < 1 := by
      rw [div_lt_one (by positivity)]; linarith [h4 m]
    have hg := (hasSum_geometric_of_lt_one hr0 hr1).mul_left ((3 : ℝ) / 2 ^ (m + n + 1))
    have hfun : f m = fun s => (3 : ℝ) / 2 ^ (m + n + 1) * ((3 : ℝ) / 2 ^ (m + n + 1)) ^ s := by
      funext s; rw [key]; ring
    have hne : (2 : ℝ) ^ (m + n + 1) - 3 ≠ 0 := by linarith [h4 m]
    have hne2 : (2 : ℝ) ^ (m + n + 1) ≠ 0 := by positivity
    have hval : (3 : ℝ) / (2 ^ (m + n + 1) - 3) =
        3 / 2 ^ (m + n + 1) * (1 - 3 / 2 ^ (m + n + 1))⁻¹ := by
      field_simp
    rw [hfun, hval]
    exact hg
  have inner2 : ∀ s, HasSum (fun m => f m s) (((3 : ℝ) / 2 ^ n) ^ (s + 1) / (2 ^ (s + 1) - 1)) := by
    intro s
    have hr0 : 0 ≤ (1 : ℝ) / 2 ^ (s + 1) := by positivity
    have hr1 : (1 : ℝ) / 2 ^ (s + 1) < 1 := by
      rw [div_lt_one (by positivity)]
      exact one_lt_pow₀ (by norm_num) (by omega)
    have hg := (hasSum_geometric_of_lt_one hr0 hr1).mul_left (((3 : ℝ) / 2 ^ (n + 1)) ^ (s + 1))
    have hne : (2 : ℝ) ^ (s + 1) - 1 ≠ 0 := by
      have : (1 : ℝ) < 2 ^ (s + 1) := one_lt_pow₀ (by norm_num) (by omega)
      linarith
    have hval : ((3 : ℝ) / 2 ^ n) ^ (s + 1) / (2 ^ (s + 1) - 1) =
        ((3 : ℝ) / 2 ^ (n + 1)) ^ (s + 1) * (1 - 1 / 2 ^ (s + 1))⁻¹ := by
      rw [div_pow, div_pow, ← pow_mul, ← pow_mul, show (n + 1) * (s + 1) = n * (s + 1) + (s + 1) by ring, pow_add]
      field_simp
      exact pow_add _ _ _
    rw [hval]
    exact hg
  have hsum1 : Summable (fun m : ℕ => (3 : ℝ) / (2 ^ (m + n + 1) - 3)) := by
    refine Summable.of_nonneg_of_le (fun m => ?_) (fun m => ?_) ((summable_geometric_two).mul_left 3)
    · have := h4 m; exact div_nonneg (by norm_num) (by linarith)
    · have hpow : (2 : ℝ) ^ (m + 2) ≤ 2 ^ (m + n + 1) := pow_le_pow_right₀ (by norm_num) (by omega)
      have h1 : (1 : ℝ) ≤ 2 ^ m := one_le_pow₀ (by norm_num)
      have h2 : (2 : ℝ) ^ (m + 2) = 4 * 2 ^ m := by rw [pow_add]; ring
      calc (3 : ℝ) / (2 ^ (m + n + 1) - 3) ≤ 3 / 2 ^ m :=
            div_le_div_of_nonneg_left (by norm_num) (by positivity) (by linarith)
        _ = 3 * (1 / 2) ^ m := by rw [one_div_pow]; ring
  have hU : Summable (Function.uncurry f) := by
    refine (summable_prod_of_nonneg (fun p => hpos p.1 p.2)).mpr ⟨fun m => (inner1 m).summable, ?_⟩
    exact hsum1.congr (fun m => ((inner1 m).tsum_eq).symm)
  have hcomm := hU.tsum_comm' (fun m => (inner1 m).summable) (fun s => (inner2 s).summable)
  rw [show (∑' m : ℕ, (3 : ℝ) / (2 ^ (m + n + 1) - 3)) = ∑' m, ∑' s, f m s from
    tsum_congr (fun m => ((inner1 m).tsum_eq).symm)]
  rw [← hcomm]
  exact tsum_congr (fun s => (inner2 s).tsum_eq)
