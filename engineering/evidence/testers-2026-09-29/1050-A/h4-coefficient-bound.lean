import Mathlib

theorem prod_one_sub_ge (s : Finset ℕ) (a : ℕ → ℝ) (h0 : ∀ i ∈ s, 0 ≤ a i) (h1 : ∀ i ∈ s, a i ≤ 1) :
    1 - ∑ i ∈ s, a i ≤ ∏ i ∈ s, (1 - a i) := by
  induction s using Finset.induction_on with
  | empty => simp
  | insert j s hj ih =>
    rw [Finset.sum_insert hj, Finset.prod_insert hj]
    have ih' := ih (fun i hi => h0 i (Finset.mem_insert_of_mem hi)) (fun i hi => h1 i (Finset.mem_insert_of_mem hi))
    have haj0 := h0 j (Finset.mem_insert_self j s)
    have haj1 := h1 j (Finset.mem_insert_self j s)
    have hP : 0 ≤ ∏ i ∈ s, (1 - a i) :=
      Finset.prod_nonneg (fun i hi => by linarith [h1 i (Finset.mem_insert_of_mem hi)])
    have hP1 : ∏ i ∈ s, (1 - a i) ≤ 1 :=
      Finset.prod_le_one (fun i hi => by linarith [h1 i (Finset.mem_insert_of_mem hi)])
        (fun i hi => by linarith [h0 i (Finset.mem_insert_of_mem hi)])
    nlinarith

theorem nd_bound (n K : ℕ) (hn : 1 ≤ n) (hK : 2 * n + 1 ≤ K) :
    0 < (∏ L ∈ Finset.Ioc n (2 * n), ((2 : ℝ) ^ K - 2 ^ L)) / ∏ i ∈ Finset.range (n + 1), ((2 : ℝ) ^ K - 2 ^ i) ∧
    (∏ L ∈ Finset.Ioc n (2 * n), ((2 : ℝ) ^ K - 2 ^ L)) / ∏ i ∈ Finset.range (n + 1), ((2 : ℝ) ^ K - 2 ^ i)
      ≤ 2 * (1 / 2) ^ K := by
  have hlt : ∀ i, i < K → (0 : ℝ) < 2 ^ K - 2 ^ i := fun i hi => by
    have : (2 : ℝ) ^ i < 2 ^ K := pow_lt_pow_right₀ (by norm_num) hi
    linarith
  have hNpos : 0 < ∏ L ∈ Finset.Ioc n (2 * n), ((2 : ℝ) ^ K - 2 ^ L) :=
    Finset.prod_pos (fun L hL => hlt L (by have := Finset.mem_Ioc.mp hL; omega))
  have hDpos : 0 < ∏ i ∈ Finset.range (n + 1), ((2 : ℝ) ^ K - 2 ^ i) :=
    Finset.prod_pos (fun i hi => hlt i (by have := Finset.mem_range.mp hi; omega))
  refine ⟨div_pos hNpos hDpos, ?_⟩
  have hN : ∏ L ∈ Finset.Ioc n (2 * n), ((2 : ℝ) ^ K - 2 ^ L) ≤ (2 ^ K) ^ n := by
    have := Finset.prod_le_prod (s := Finset.Ioc n (2 * n)) (f := fun L => (2 : ℝ) ^ K - 2 ^ L) (g := fun _ => (2 : ℝ) ^ K)
      (fun L hL => le_of_lt (hlt L (by have := Finset.mem_Ioc.mp hL; omega))) (fun L _ => by
        have : (0 : ℝ) < 2 ^ L := by positivity
        linarith)
    rw [Finset.prod_const, Nat.card_Ioc, show 2 * n - n = n by omega] at this
    exact this
  have hD : (2 ^ K) ^ (n + 1) / 2 ≤ ∏ i ∈ Finset.range (n + 1), ((2 : ℝ) ^ K - 2 ^ i) := by
    have hfac : ∀ i ∈ Finset.range (n + 1), (2 : ℝ) ^ K - 2 ^ i = 2 ^ K * (1 - (1 / 2) ^ (K - i)) := by
      intro i hi
      have hiK : i ≤ K := by have := Finset.mem_range.mp hi; omega
      have e : (2 : ℝ) ^ K = 2 ^ i * 2 ^ (K - i) := by rw [← pow_add]; congr 1; omega
      rw [mul_sub, mul_one, one_div_pow, mul_one_div, e]
      field_simp
    rw [Finset.prod_congr rfl hfac, Finset.prod_mul_distrib, Finset.prod_const, Finset.card_range]
    have hsum : ∑ i ∈ Finset.range (n + 1), ((1 : ℝ) / 2) ^ (K - i) ≤ 1 / 2 := by
      have e : ∀ i ∈ Finset.range (n + 1), ((1 : ℝ) / 2) ^ (K - i) = (1 / 2) ^ (K - n) * (1 / 2) ^ (n - i) := by
        intro i hi
        have := Finset.mem_range.mp hi
        rw [← pow_add]; congr 1; omega
      rw [Finset.sum_congr rfl e, ← Finset.mul_sum]
      have hg : ∑ i ∈ Finset.range (n + 1), ((1 : ℝ) / 2) ^ (n - i) ≤ 2 := by
        have hr := Finset.sum_range_reflect (fun i => ((1 : ℝ) / 2) ^ i) (n + 1)
        simp only [Nat.add_sub_cancel] at hr
        rw [hr]
        exact sum_geometric_two_le (n + 1)
      have hk : ((1 : ℝ) / 2) ^ (K - n) ≤ (1 / 2) ^ 2 :=
        pow_le_pow_of_le_one (by norm_num) (by norm_num) (by omega)
      have hpos : 0 ≤ ((1 : ℝ) / 2) ^ (K - n) := by positivity
      nlinarith
    have hprod := prod_one_sub_ge (Finset.range (n + 1)) (fun i => ((1 : ℝ) / 2) ^ (K - i))
      (fun i _ => by positivity) (fun i _ => pow_le_one₀ (by norm_num) (by norm_num))
    have h2K : (0 : ℝ) < (2 ^ K) ^ (n + 1) := by positivity
    nlinarith
  rw [div_le_iff₀ hDpos]
  have h2K : (2 : ℝ) ^ K * (1 / 2) ^ K = 1 := by rw [← mul_pow]; norm_num
  have e2 : 2 * (1 / 2 : ℝ) ^ K * ((2 ^ K) ^ (n + 1) / 2) = (2 ^ K) ^ n := by
    rw [pow_succ]
    calc 2 * (1 / 2 : ℝ) ^ K * ((2 ^ K) ^ n * 2 ^ K / 2) = (2 ^ K * (1 / 2) ^ K) * (2 ^ K) ^ n := by ring
      _ = (2 ^ K) ^ n := by rw [h2K, one_mul]
  calc ∏ L ∈ Finset.Ioc n (2 * n), ((2 : ℝ) ^ K - 2 ^ L) ≤ (2 ^ K) ^ n := hN
    _ = 2 * (1 / 2) ^ K * ((2 ^ K) ^ (n + 1) / 2) := e2.symm
    _ ≤ 2 * (1 / 2) ^ K * ∏ i ∈ Finset.range (n + 1), ((2 : ℝ) ^ K - 2 ^ i) := by gcongr
