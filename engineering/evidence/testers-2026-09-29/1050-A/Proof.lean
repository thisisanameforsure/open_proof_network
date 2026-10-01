import Mathlib
import Nodes.«spec-440db0f9».Context

/-- erdos-1050, hole hden (erdos-1050--h1-v2--h3), ingredient 1 of annex 4670684d2f0d on that node:
the Gaussian binomial coefficient at q = 2, written as the same product of quotients that `Qc` in
h3 and h4 uses, is an integer. For k > n a factor 2^(n - i) - 1 with truncated n - i = 0 is 0, so
the product is 0 there, which is also the Gaussian binomial's value. -/
theorem erdos_1050_gauss_binom_two_int (n k : ℕ) :
    ∃ z : ℤ, (z : ℚ) = ∏ i ∈ Finset.range k, ((2 : ℚ) ^ (n - i) - 1) / ((2 : ℚ) ^ (i + 1) - 1) := by
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
