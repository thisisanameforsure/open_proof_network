import Mathlib

open scoped ArithmeticFunction.omega

theorem Opn.erdos_69_rational_tails_periodic :
    ∀ (f : ℕ → ℕ) (q : ℚ), Summable (fun n : ℕ => (f n : ℝ) / 2 ^ n) →
      (q : ℝ) = ∑' n : ℕ, (f n : ℝ) / 2 ^ n →
      ∃ p N₀ : ℕ, 0 < p ∧ ∀ n n' : ℕ, N₀ ≤ n → N₀ ≤ n' → n ≡ n' [MOD p] →
        ∃ z : ℤ, ∑' j : ℕ, (f (n + 1 + j) : ℝ) / 2 ^ (j + 1)
          - ∑' j : ℕ, (f (n' + 1 + j) : ℝ) / 2 ^ (j + 1) = z := by
  intro f q hs hq
  -- (a) the tail formula: tail_n = 2^n x - A_n with A_n a natural number
  have htail : ∀ n : ℕ, ∑' j : ℕ, (f (n + 1 + j) : ℝ) / 2 ^ (j + 1)
      = 2 ^ n * ∑' m : ℕ, (f m : ℝ) / 2 ^ m
        - ((∑ i ∈ Finset.range (n + 1), f i * 2 ^ (n - i) : ℕ) : ℝ) := by
    intro n
    have h1 := Summable.sum_add_tsum_nat_add (n + 1) hs
    have h2 : ∀ j : ℕ, (f (j + (n + 1)) : ℝ) / 2 ^ (j + (n + 1))
        = (1 / 2 ^ n) * ((f (n + 1 + j) : ℝ) / 2 ^ (j + 1)) := by
      intro j
      rw [show j + (n + 1) = n + 1 + j by omega, show n + 1 + j = n + (j + 1) by omega, pow_add]
      field_simp
    rw [tsum_congr h2, tsum_mul_left] at h1
    have h3 : (2 : ℝ) ^ n * ∑ i ∈ Finset.range (n + 1), (f i : ℝ) / 2 ^ i
        = ((∑ i ∈ Finset.range (n + 1), f i * 2 ^ (n - i) : ℕ) : ℝ) := by
      push_cast
      rw [Finset.mul_sum]
      refine Finset.sum_congr rfl (fun i hi => ?_)
      have hi' : i ≤ n := Nat.lt_succ_iff.1 (Finset.mem_range.1 hi)
      have : (2 : ℝ) ^ n = 2 ^ (n - i) * 2 ^ i := by
        rw [← pow_add, Nat.sub_add_cancel hi']
      rw [this]
      field_simp
    rw [← h1, mul_add, h3, ← mul_assoc, mul_one_div_cancel (by positivity), one_mul]
    ring
  -- (b) 2^n q is eventually periodic mod 1 (pigeonhole on 2^n num mod den)
  have hper : ∃ p N₀ : ℕ, 0 < p ∧ ∀ n n' : ℕ, N₀ ≤ n → N₀ ≤ n' → n ≡ n' [MOD p] →
      ∃ z : ℤ, (2 : ℝ) ^ n * (q : ℝ) - 2 ^ n' * (q : ℝ) = z := by
    have : NeZero q.den := ⟨q.den_nz⟩
    let g : ℕ → ZMod q.den := fun n => ((2 ^ n * q.num : ℤ) : ZMod q.den)
    obtain ⟨x, y, hxy, hg⟩ := Finite.exists_ne_map_eq_of_infinite g
    have hkey : ∃ n₀ p : ℕ, 0 < p ∧ (q.den : ℤ) ∣ 2 ^ (n₀ + p) * q.num - 2 ^ n₀ * q.num := by
      have h := (ZMod.intCast_eq_intCast_iff_dvd_sub _ _ _).1 hg
      rcases lt_or_gt_of_ne hxy with hlt | hlt
      · refine ⟨x, y - x, by omega, ?_⟩
        rw [show x + (y - x) = y by omega]
        exact h
      · refine ⟨y, x - y, by omega, ?_⟩
        rw [show y + (x - y) = x by omega, ← dvd_neg, neg_sub]
        exact h
    obtain ⟨n₀, p, hp, hd⟩ := hkey
    have hmul : ∀ m t : ℕ, (q.den : ℤ) ∣ 2 ^ (n₀ + t + m * p) * q.num - 2 ^ (n₀ + t) * q.num := by
      intro m t
      induction m with
      | zero => simp
      | succ m ih =>
        have e : (2 : ℤ) ^ (n₀ + t + (m + 1) * p) * q.num - 2 ^ (n₀ + t) * q.num
            = 2 ^ (t + m * p) * (2 ^ (n₀ + p) * q.num - 2 ^ n₀ * q.num)
              + (2 ^ (n₀ + t + m * p) * q.num - 2 ^ (n₀ + t) * q.num) := by
          rw [show n₀ + t + (m + 1) * p = (t + m * p) + (n₀ + p) by ring,
            show n₀ + t + m * p = (t + m * p) + n₀ by ring, pow_add, pow_add]
          ring
        rw [e]
        exact dvd_add (dvd_mul_of_dvd_right hd _) ih
    have hle : ∀ n n' : ℕ, n₀ ≤ n → n ≤ n' → n ≡ n' [MOD p] →
        ∃ z : ℤ, (2 : ℝ) ^ n * (q : ℝ) - 2 ^ n' * (q : ℝ) = z := by
      intro n n' hn hnn' hmod
      obtain ⟨m, hm⟩ := (Nat.modEq_iff_dvd' hnn').1 hmod
      have h1 := hmul m (n - n₀)
      rw [show n₀ + (n - n₀) = n by omega, show n + m * p = n' by
        rw [mul_comm]; omega] at h1
      obtain ⟨w, hw⟩ := h1
      refine ⟨-w, ?_⟩
      have hden : (q.den : ℝ) ≠ 0 := by exact_mod_cast q.den_nz
      have hw' : (2 : ℝ) ^ n' * (q.num : ℝ) - 2 ^ n * (q.num : ℝ) = (q.den : ℝ) * (w : ℝ) := by
        exact_mod_cast hw
      rw [Rat.cast_def]
      field_simp
      push_cast
      linarith
    refine ⟨p, n₀, hp, fun n n' hn hn' hmod => ?_⟩
    rcases le_total n n' with h | h
    · exact hle n n' hn h hmod
    · obtain ⟨z, hz⟩ := hle n' n hn' h hmod.symm
      exact ⟨-z, by push_cast; linarith⟩
  -- (c) combine
  obtain ⟨p, N₀, hp, h⟩ := hper
  refine ⟨p, N₀, hp, fun n n' hn hn' hmod => ?_⟩
  obtain ⟨z, hz⟩ := h n n' hn hn' hmod
  refine ⟨z - ((∑ i ∈ Finset.range (n + 1), f i * 2 ^ (n - i) : ℕ) : ℤ)
    + ((∑ i ∈ Finset.range (n' + 1), f i * 2 ^ (n' - i) : ℕ) : ℤ), ?_⟩
  rw [htail n, htail n', ← hq]
  push_cast
  linarith
