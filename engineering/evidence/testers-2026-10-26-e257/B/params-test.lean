import Mathlib

private def dd (n : ℕ) : ℕ := n.divisors.card

/- The divisor count of a product of squares of distinct primes. -/
private lemma dd_prod_sq {ι : Type*} (S : Finset ι) (pr : ι → ℕ) (hp : ∀ i ∈ S, (pr i).Prime)
    (hinj : Set.InjOn pr (S : Set ι)) : dd (∏ i ∈ S, pr i ^ 2) = 3 ^ S.card := by
  classical
  induction S using Finset.induction_on with
  | empty => simp [dd]
  | insert a S haS ih =>
    rw [Finset.prod_insert haS, Finset.card_insert_of_notMem haS, pow_succ (3 : ℕ) S.card]
    have hpa := hp a (Finset.mem_insert_self _ _)
    have hcop : Nat.Coprime (pr a ^ 2) (∏ i ∈ S, pr i ^ 2) := by
      apply Nat.Coprime.prod_right
      intro i hi
      apply Nat.Coprime.pow
      rw [Nat.coprime_primes hpa (hp i (Finset.mem_insert_of_mem hi))]
      intro h
      exact haS (hinj (Finset.mem_insert_self _ _) (Finset.mem_insert_of_mem hi) h ▸ hi)
    unfold dd
    rw [Nat.Coprime.card_divisors_mul hcop]
    have h3 : (pr a ^ 2).divisors.card = 3 := by
      rw [Nat.divisors_prime_pow hpa 2, Finset.card_map, Finset.card_range]
    rw [h3]
    have ih' := ih (fun i hi => hp i (Finset.mem_insert_of_mem hi))
      (hinj.mono (by simp))
    unfold dd at ih'
    rw [ih', mul_comm]

private lemma eight_mul_le_two_pow {q : ℕ} (hq : 6 ≤ q) : 8 * q ≤ 2 ^ q := by
  induction q with
  | zero => omega
  | succ n ih =>
    rcases Nat.lt_or_ge n 6 with h | h
    · interval_cases n <;> first | omega | norm_num
    · have := ih h
      rw [pow_succ]; omega

private lemma exists_param2 (b P : ℕ) :
    ∃ m : ℕ, b ≤ m ∧ 1 ≤ m ∧ 4 * m * (3 + 2000 * P ^ 3 * m ^ 12) + 1 < 2 ^ m := by
  have h := tendsto_pow_const_div_const_pow_of_one_lt 13 (r := (2:ℝ)) (by norm_num)
  have hC : (0 : ℝ) < 1 / (13 + 8000 * (P : ℝ) ^ 3) := by positivity
  have h2 := (h.eventually (gt_mem_nhds hC)).and (Filter.eventually_ge_atTop (max b 1))
  obtain ⟨m, hm, hmb⟩ := h2.exists
  refine ⟨m, le_of_max_le_left hmb, le_of_max_le_right hmb, ?_⟩
  have hm1 : (1 : ℝ) ≤ m := by exact_mod_cast le_of_max_le_right hmb
  have h13 : (m : ℝ) ^ 13 < 1 / (13 + 8000 * (P : ℝ) ^ 3) * 2 ^ m := by
    rwa [div_lt_iff₀ (by positivity)] at hm
  have hpos : (0 : ℝ) < 13 + 8000 * (P : ℝ) ^ 3 := by positivity
  have hkey : (13 + 8000 * (P : ℝ) ^ 3) * (m : ℝ) ^ 13 < 2 ^ m := by
    rw [div_mul_eq_mul_div, one_mul, lt_div_iff₀ hpos] at h13
    linarith
  have hle : (4 * m * (3 + 2000 * P ^ 3 * m ^ 12) + 1 : ℝ) ≤ (13 + 8000 * (P : ℝ) ^ 3) * (m : ℝ) ^ 13 := by
    have hm13 : (m : ℝ) ≤ (m : ℝ) ^ 13 := le_self_pow₀ hm1 (by norm_num)
    have h1 : (1 : ℝ) ≤ (m : ℝ) ^ 13 := one_le_pow₀ hm1
    have hP0 : (0 : ℝ) ≤ (P : ℝ) ^ 3 := by positivity
    nlinarith
  have : (4 * m * (3 + 2000 * P ^ 3 * m ^ 12) + 1 : ℝ) < 2 ^ m := lt_of_le_of_lt hle hkey
  exact_mod_cast this

theorem params_test_end : True := trivial
