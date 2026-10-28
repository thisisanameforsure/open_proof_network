import Mathlib

theorem Opn.erdos_68 :
    Irrational (∑' n : ℕ, 1 / ((n + 2).factorial - 1 : ℝ)) := by
  -- approach: factorial base: (N+2)!·S is the finite sum A_N plus a tail in (0,1/2); a rational S makes (N+2)!·S an integer
  -- licence: CC-BY-4.0
  -- label: the series converges
  -- claim: $\sum_{n\ge 2} \frac{1}{n!-1}$ converges
  have h_summ : Summable (fun n : ℕ => 1 / ((n + 2).factorial - 1 : ℝ)) := sorry
  -- label: the scaled tail lies in (0, 1/2)
  -- claim: $0 < (N+2)!\sum_{m\ge N+3}\frac{1}{m!-1} < \frac12$ for $N \ge 1$
  have h_tail : ∀ N : ℕ, 1 ≤ N →
      0 < ((N + 2).factorial : ℝ) * ∑' i : ℕ, 1 / ((i + (N + 1) + 2).factorial - 1 : ℝ) ∧
      ((N + 2).factorial : ℝ) * ∑' i : ℕ, 1 / ((i + (N + 1) + 2).factorial - 1 : ℝ) < 1 / 2 := sorry
  -- label: the finite sums' fractional parts
  -- claim: for infinitely many $N$, the fractional part of $(N+2)!\sum_{m=2}^{N+2}\frac{1}{m!-1}$ is at most $\frac12$
  have h_open : ∀ M : ℕ, ∃ N : ℕ, M ≤ N ∧
      Int.fract (((N + 2).factorial : ℝ) * ∑ n ∈ Finset.range (N + 1), 1 / ((n + 2).factorial - 1 : ℝ)) ≤ 1 / 2 := sorry
  rintro ⟨r, hr⟩
  obtain ⟨N, hMN, hfr⟩ := h_open (r.den + 1)
  have hN1 : 1 ≤ N := by omega
  obtain ⟨hB0, hB1⟩ := h_tail N hN1
  set B := ((N + 2).factorial : ℝ) * ∑' i : ℕ, 1 / ((i + (N + 1) + 2).factorial - 1 : ℝ) with hB
  set A := ((N + 2).factorial : ℝ) * ∑ n ∈ Finset.range (N + 1), 1 / ((n + 2).factorial - 1 : ℝ) with hA
  have hsplit := h_summ.sum_add_tsum_nat_add (N + 1)
  have hden : r.den ∣ (N + 2).factorial := Nat.dvd_factorial r.den_pos (by omega)
  obtain ⟨k, hk⟩ := hden
  have hint : ((N + 2).factorial : ℝ) * (r : ℝ) = ((k * r.num : ℤ) : ℝ) := by
    have h1 : (r : ℝ) * r.den = r.num := by exact_mod_cast Rat.mul_den_eq_num r
    rw [hk]; push_cast; linear_combination (k : ℝ) * h1
  have hAB : A + B = ((k * r.num : ℤ) : ℝ) := by
    rw [hA, hB, ← mul_add, hsplit, ← hr, hint]
  have hAeq : A = ((k * r.num : ℤ) : ℝ) - B := by linarith
  have hBfr : Int.fract B = B := Int.fract_eq_self.mpr ⟨hB0.le, by linarith⟩
  have hfB : Int.fract B ≠ 0 := by rw [hBfr]; exact hB0.ne'
  have : Int.fract A = 1 - B := by
    rw [hAeq, sub_eq_add_neg, Int.fract_intCast_add, Int.fract_neg hfB, hBfr]
  linarith
