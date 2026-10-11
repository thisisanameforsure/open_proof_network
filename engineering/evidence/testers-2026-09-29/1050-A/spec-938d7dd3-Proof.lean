import Mathlib
import Nodes.«spec-938d7dd3».Context

/-- erdos-1050, hole hden (erdos-1050--h1-v2--h3), the Qx half of its integrality claim, from
annex 4670684d2f0d on that node: with `Qc` and `Qx` exactly as in h3, 2^(n(n+1)/2) * Qx n is an
integer. Each Qc n k is (-1)^k 2^(k(k-1)/2) times two Gaussian binomials at q = 2, integers by
spec-440db0f9 (the second is [2n-k, n]_2), so its term Qc n k (3/2^n)^k has 2-denominator at most
2^(nk - k(k-1)/2) ≤ 2^(n(n+1)/2), since n(n+1)/2 + k(k-1)/2 - nk = (n-k)(n-k+1)/2 ≥ 0. Hence
d = 2^(n(n+1)/2) times any odd factor clears Qx n; with spec-1a5ab7c3 this leaves only the
2-adic part of Aq n (the annex's v2(p_k(n)) ≥ k(k-1)/2) open for h3's integrality. -/
theorem erdos_1050_hden_Qx_two_power : ∀ (Qc : ℕ → ℕ → ℚ),
    (Qc = fun (n k : ℕ) =>
      ((-1 : ℚ) ^ k * (2 : ℚ) ^ (k * (k - 1) / 2) *
          ∏ i ∈ Finset.range k, ((2 : ℚ) ^ (n - i) - 1) / ((2 : ℚ) ^ (i + 1) - 1)) *
        ∏ i ∈ Finset.range n, ((2 : ℚ) ^ (2 * n - k - i) - 1) / ((2 : ℚ) ^ (i + 1) - 1)) →
    ∀ (Qx : ℕ → ℚ),
      (Qx = fun (n : ℕ) => ∑ k ∈ Finset.range (n + 1), Qc n k * ((3 : ℚ) / (2 : ℚ) ^ n) ^ k) →
        ∀ (n : ℕ), ∃ z : ℤ, (z : ℚ) = (2 : ℚ) ^ (n * (n + 1) / 2) * Qx n := by
  intro Qc hQc Qx hQx n
  subst hQx
  show ∃ z : ℤ, (z : ℚ) = (2 : ℚ) ^ (n * (n + 1) / 2) *
      ∑ k ∈ Finset.range (n + 1), Qc n k * ((3 : ℚ) / (2 : ℚ) ^ n) ^ k
  have gauss : ∀ n k : ℕ,
      ∃ z : ℤ, (z : ℚ) = ∏ i ∈ Finset.range k, ((2 : ℚ) ^ (n - i) - 1) / ((2 : ℚ) ^ (i + 1) - 1) := by
    intro n k
    have hD : ∀ j : ℕ, ((2 : ℚ) ^ (j + 1) - 1) ≠ 0 := by
      intro j
      have h1 : (1 : ℚ) < 2 ^ (j + 1) := one_lt_pow₀ (by norm_num) (by omega)
      exact ne_of_gt (sub_pos.mpr h1)
    have hDk : ∀ k : ℕ, (∏ i ∈ Finset.range k, ((2 : ℚ) ^ (i + 1) - 1)) ≠ 0 := by
      intro k
      exact Finset.prod_ne_zero_iff.mpr (fun i _ => hD i)
    have key : ∀ m j : ℕ,
        (∏ i ∈ Finset.range (j + 1), ((2 : ℚ) ^ (m + 1 - i) - 1) / ((2 : ℚ) ^ (i + 1) - 1)) =
          (∏ i ∈ Finset.range j, ((2 : ℚ) ^ (m - i) - 1) / ((2 : ℚ) ^ (i + 1) - 1)) +
          2 ^ (j + 1) *
            ∏ i ∈ Finset.range (j + 1), ((2 : ℚ) ^ (m - i) - 1) / ((2 : ℚ) ^ (i + 1) - 1) := by
      intro m j
      simp only [Finset.prod_div_distrib]
      rw [Finset.prod_range_succ' (fun i => (2 : ℚ) ^ (m + 1 - i) - 1)]
      have hshift : ∀ i : ℕ, m + 1 - (i + 1) = m - i := fun i => by omega
      simp only [hshift, Nat.sub_zero]
      rw [Finset.prod_range_succ (fun i => (2 : ℚ) ^ (m - i) - 1),
        Finset.prod_range_succ (fun i => (2 : ℚ) ^ (i + 1) - 1)]
      have hDj := hDk j
      have hj := hD j
      by_cases hjm : j ≤ m
      · have e : (2 : ℚ) ^ (m + 1) = 2 ^ (m - j) * 2 ^ (j + 1) := by
          rw [← pow_add]
          congr 1
          omega
        rw [e]
        field_simp
        ring
      · have hz : (∏ i ∈ Finset.range j, ((2 : ℚ) ^ (m - i) - 1)) = 0 :=
          Finset.prod_eq_zero (i := m) (Finset.mem_range.mpr (by omega)) (by simp)
        rw [hz]
        simp
    have main : ∀ m j : ℕ, ∃ z : ℤ,
        (z : ℚ) = ∏ i ∈ Finset.range j, ((2 : ℚ) ^ (m - i) - 1) / ((2 : ℚ) ^ (i + 1) - 1) := by
      intro m
      induction m with
      | zero =>
        intro j
        cases j with
        | zero => exact ⟨1, by simp⟩
        | succ j =>
          refine ⟨0, ?_⟩
          rw [Finset.prod_eq_zero (i := 0) (by simp) (by simp)]
          simp
      | succ m ih =>
        intro j
        cases j with
        | zero => exact ⟨1, by simp⟩
        | succ j =>
          obtain ⟨a, ha⟩ := ih j
          obtain ⟨b, hb⟩ := ih (j + 1)
          refine ⟨a + 2 ^ (j + 1) * b, ?_⟩
          rw [key, ← ha, ← hb]
          push_cast
          ring
    exact main n k
  have hterm : ∀ k ∈ Finset.range (n + 1), ∃ z : ℤ,
      (z : ℚ) = (2 : ℚ) ^ (n * (n + 1) / 2) * (Qc n k * ((3 : ℚ) / (2 : ℚ) ^ n) ^ k) := by
    intro k hk
    have hkn : k ≤ n := Nat.lt_succ_iff.mp (Finset.mem_range.mp hk)
    obtain ⟨a, ha⟩ := gauss n k
    obtain ⟨b, hb⟩ := gauss (2 * n - k) n
    obtain ⟨m, rfl⟩ := Nat.exists_eq_add_of_le hkn
    have hexp : (k + m) * (k + m + 1) / 2 + k * (k - 1) / 2 = m * (m + 1) / 2 + (k + m) * k := by
      have e1 : 2 * ((k + m) * (k + m + 1) / 2) = (k + m) * (k + m + 1) :=
        Nat.two_mul_div_two_of_even (Nat.even_mul_succ_self _)
      have e2 : 2 * (k * (k - 1) / 2) = k * (k - 1) :=
        Nat.two_mul_div_two_of_even (Nat.even_mul_pred_self _)
      have e3 : 2 * (m * (m + 1) / 2) = m * (m + 1) :=
        Nat.two_mul_div_two_of_even (Nat.even_mul_succ_self _)
      rcases k with _ | j
      · simp
      · simp only [Nat.add_sub_cancel] at e2 ⊢
        nlinarith [e1, e2, e3]
    refine ⟨(-1) ^ k * 3 ^ k * 2 ^ (m * (m + 1) / 2) * a * b, ?_⟩
    have hpow : (2 : ℚ) ^ ((k + m) * (k + m + 1) / 2) * (2 : ℚ) ^ (k * (k - 1) / 2) =
        (2 : ℚ) ^ (m * (m + 1) / 2) * ((2 : ℚ) ^ (k + m)) ^ k := by
      rw [← pow_add, ← pow_mul, ← pow_add, hexp]
    have h2 : ((2 : ℚ) ^ (k + m)) ≠ 0 := by positivity
    rw [hQc]
    simp only []
    rw [← ha, ← hb]
    push_cast
    rw [div_pow, mul_div_assoc']
    field_simp
    linear_combination -(a : ℚ) * b * hpow
  choose! g hg using hterm
  refine ⟨∑ k ∈ Finset.range (n + 1), g k, ?_⟩
  push_cast
  rw [Finset.mul_sum]
  exact Finset.sum_congr rfl (fun k hk => hg k hk)
