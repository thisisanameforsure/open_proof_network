/-
Copyright 2025 The Formal Conjectures Authors.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
-/

import Mathlib

/-! Erdős problem 68 — erdosproblems.com/68, imported from
google-deepmind/formal-conjectures (FormalConjectures/ErdosProblems/68.lean at
c7f31d5fd3d2ca3d69979f2d213eb9b58fe956ae, Apache-2.0), adapted to D-3's shape: the
registry states a yes/no question as `answer(sorry) ↔ P`; this states P, its affirmative
reading (F11-Q24). Listed, not claimable, at Stage 0. -/

private theorem e68_summable : Summable (fun n : ℕ => 1 / ((n + 2).factorial - 1 : ℝ)) := by
  have hf : Summable (fun n : ℕ => 2 * (1 / ((n + 2).factorial : ℝ))) := by
    have h := Real.summable_pow_div_factorial 1
    have h2 := (summable_nat_add_iff 2).mpr h
    simpa using h2.mul_left 2
  refine Summable.of_nonneg_of_le (fun n => ?_) (fun n => ?_) hf
  · have : 2 ≤ (n + 2).factorial := by
      calc 2 = (2 : ℕ).factorial := rfl
        _ ≤ (n + 2).factorial := Nat.factorial_le (by omega)
    have : (2 : ℝ) ≤ ((n + 2).factorial : ℝ) := by exact_mod_cast this
    apply div_nonneg zero_le_one; linarith
  · have : 2 ≤ (n + 2).factorial := by
      calc 2 = (2 : ℕ).factorial := rfl
        _ ≤ (n + 2).factorial := Nat.factorial_le (by omega)
    have h2 : (2 : ℝ) ≤ ((n + 2).factorial : ℝ) := by exact_mod_cast this
    rw [mul_one_div, div_le_div_iff₀ (by linarith) (by linarith)]
    linarith

private lemma e68_tail_term_le (K i : ℕ) (hK : 1 ≤ K) :
    (K.factorial : ℝ) * (1 / ((i + (K - 1) + 2).factorial - 1 : ℝ)) ≤ 2 * (1 / ((K : ℝ) + 1)) ^ (i + 1) := by
  have hidx : i + (K - 1) + 2 = K + (i + 1) := by omega
  rw [hidx]
  have hfac : (K.factorial : ℝ) * ((K : ℝ) + 1) ^ (i + 1) ≤ ((K + (i + 1)).factorial : ℝ) := by
    exact_mod_cast Nat.factorial_mul_pow_le_factorial
  have hKpos : (0 : ℝ) < K.factorial := by exact_mod_cast Nat.factorial_pos K
  have hpow : (0 : ℝ) < ((K : ℝ) + 1) ^ (i + 1) := by positivity
  have hbig : (2 : ℝ) ≤ ((K + (i + 1)).factorial : ℝ) := by
    have : 2 ≤ (K + (i + 1)).factorial := by
      calc 2 = (2 : ℕ).factorial := rfl
        _ ≤ (K + (i + 1)).factorial := Nat.factorial_le (by omega)
    exact_mod_cast this
  have hden : (0 : ℝ) < ((K + (i + 1)).factorial : ℝ) - 1 := by linarith
  rw [div_pow, one_pow, mul_one_div, mul_one_div, div_le_iff₀ hden]
  rw [div_mul_eq_mul_div, le_div_iff₀ hpow]
  nlinarith

private theorem e68_tail_bound : ∀ N : ℕ, 3 ≤ N →
      0 < ((N + 2).factorial : ℝ) * ∑' i : ℕ, 1 / ((i + (N + 1) + 2).factorial - 1 : ℝ) ∧
      ((N + 2).factorial : ℝ) * ∑' i : ℕ, 1 / ((i + (N + 1) + 2).factorial - 1 : ℝ) < 1 / 2 := by
  intro N hN
  set K := N + 2 with hKdef
  have hK1 : 1 ≤ K := by omega
  have hKm : K - 1 = N + 1 := by omega
  have hKpos : (0 : ℝ) < K.factorial := by exact_mod_cast Nat.factorial_pos K
  have hr0 : (0 : ℝ) ≤ 1 / ((K : ℝ) + 1) := by positivity
  have hr1 : 1 / ((K : ℝ) + 1) < 1 := by
    rw [div_lt_one (by positivity)]; have : (1 : ℝ) ≤ K := by exact_mod_cast hK1
    linarith
  have hgeom : Summable (fun i : ℕ => 2 * (1 / ((K : ℝ) + 1)) ^ (i + 1)) :=
    ((summable_geometric_of_lt_one hr0 hr1).mul_left (1 / ((K : ℝ) + 1))).mul_left 2 |>.congr
      (fun i => by ring)
  have hterm_pos : ∀ i : ℕ, 0 < 1 / ((i + (N + 1) + 2).factorial - 1 : ℝ) := by
    intro i
    have : 2 ≤ (i + (N + 1) + 2).factorial := by
      calc 2 = (2 : ℕ).factorial := rfl
        _ ≤ (i + (N + 1) + 2).factorial := Nat.factorial_le (by omega)
    have : (2 : ℝ) ≤ ((i + (N + 1) + 2).factorial : ℝ) := by exact_mod_cast this
    apply div_pos one_pos; linarith
  have hle : ∀ i : ℕ, 1 / ((i + (N + 1) + 2).factorial - 1 : ℝ) ≤
      (2 * (1 / ((K : ℝ) + 1)) ^ (i + 1)) / K.factorial := by
    intro i
    rw [le_div_iff₀ hKpos, mul_comm]
    have := e68_tail_term_le K i hK1
    rw [hKm] at this
    exact this
  have hsum : Summable (fun i : ℕ => 1 / ((i + (N + 1) + 2).factorial - 1 : ℝ)) :=
    Summable.of_nonneg_of_le (fun i => (hterm_pos i).le) hle (hgeom.div_const _)
  constructor
  · exact mul_pos hKpos (hsum.tsum_pos (fun i => (hterm_pos i).le) 0 (hterm_pos 0))
  · have h1 : ∑' i : ℕ, 1 / ((i + (N + 1) + 2).factorial - 1 : ℝ) ≤
        ∑' i : ℕ, (2 * (1 / ((K : ℝ) + 1)) ^ (i + 1)) / K.factorial :=
      hsum.tsum_le_tsum hle (hgeom.div_const _)
    have h2 : ∑' i : ℕ, (2 * (1 / ((K : ℝ) + 1)) ^ (i + 1)) / K.factorial = (2 / K) / K.factorial := by
      rw [tsum_div_const]
      congr 1
      have hK1' : (1 : ℝ) ≤ K := by exact_mod_cast hK1
      have hK0 : (K : ℝ) ≠ 0 := by positivity
      have : ∑' i : ℕ, 2 * (1 / ((K : ℝ) + 1)) ^ (i + 1) =
          2 * (1 / ((K : ℝ) + 1)) * ∑' i : ℕ, (1 / ((K : ℝ) + 1)) ^ i := by
        rw [← tsum_mul_left]; congr 1; ext i; ring
      rw [this, tsum_geometric_of_lt_one hr0 hr1]
      field_simp
      ring_nf
      field_simp
    have hK5 : (5 : ℝ) ≤ K := by exact_mod_cast (show 5 ≤ K by omega)
    calc ((N + 2).factorial : ℝ) * ∑' i : ℕ, 1 / ((i + (N + 1) + 2).factorial - 1 : ℝ)
        ≤ K.factorial * ((2 / K) / K.factorial) := by
          rw [← h2]; exact mul_le_mul_of_nonneg_left h1 hKpos.le
      _ = 2 / K := by field_simp
      _ < 1 / 2 := by rw [div_lt_div_iff₀ (by linarith) (by norm_num)]; linarith

theorem Opn.erdos_68 :
    Irrational (∑' n : ℕ, 1 / ((n + 2).factorial - 1 : ℝ)) := by
  -- approach: factorial base: (N+2)! times the sum is a finite sum A_N plus a tail in (0, 1/2); a rational sum makes it an integer for large N
  -- licence: CC-BY-4.0
  -- The tail bound and summability are proved above as private lemmas; what is left open
  -- is a statement about finite rational sums only.
  -- label: fractional parts of the finite sums
  -- claim: $\forall M\ \exists N \ge M,\ \left\{(N+2)!\sum_{n=0}^{N}\frac{1}{(n+2)!-1}\right\} \le \frac12$
  have h_open : ∀ M : ℕ, ∃ N : ℕ, M ≤ N ∧
      Int.fract (((N + 2).factorial : ℝ) * ∑ n ∈ Finset.range (N + 1), 1 / ((n + 2).factorial - 1 : ℝ)) ≤ 1 / 2 := sorry
  rintro ⟨r, hr⟩
  obtain ⟨N, hMN, hfr⟩ := h_open (r.den + 3)
  have hN3 : 3 ≤ N := by omega
  obtain ⟨hB0, hB1⟩ := e68_tail_bound N hN3
  set B := ((N + 2).factorial : ℝ) * ∑' i : ℕ, 1 / ((i + (N + 1) + 2).factorial - 1 : ℝ) with hB
  set A := ((N + 2).factorial : ℝ) * ∑ n ∈ Finset.range (N + 1), 1 / ((n + 2).factorial - 1 : ℝ) with hA
  have hsplit := e68_summable.sum_add_tsum_nat_add (N + 1)
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
