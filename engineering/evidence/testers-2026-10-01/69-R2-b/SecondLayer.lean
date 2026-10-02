import Mathlib
import Defs.Construction

open scoped ArithmeticFunction.omega

/-! Second layer (69-R2-b draft): h1 proved; the two lemmas h4 splits into first. -/

/-- h1, proved. -/
theorem erdos_69__h1 : ∀ (M : ℕ) (d : Fin M → Fin 6), Opn.E69.gIndex M d < 7 ^ M := by
  intro M d
  have hdig : ∀ (r : ℕ) (k : Fin 6), Opn.E69.gDigit r k ≤ 6 := by
    intro r k
    unfold Opn.E69.gDigit
    split_ifs <;> fin_cases k <;> simp
  have h1 : Opn.E69.gIndex M d ≤ ∑ r : Fin M, 7 ^ (r : ℕ) * 6 :=
    Finset.sum_le_sum fun r _ => Nat.mul_le_mul_left _ (hdig r (d r))
  have h2 : ∑ r : Fin M, 7 ^ (r : ℕ) * 6 = ∑ r ∈ Finset.range M, 7 ^ r * 6 :=
    Fin.sum_univ_eq_sum_range (fun r => 7 ^ r * 6) M
  have h3 : ∀ n : ℕ, ∑ r ∈ Finset.range n, 7 ^ r * 6 + 1 = 7 ^ n := by
    intro n
    induction n with
    | zero => simp
    | succ n ih => rw [Finset.sum_range_succ, pow_succ]; omega
  have := h3 M
  omega

/-- h4a (exact cancellation): at every depth `u ≤ 3M` the signed number of lines through any
point is zero. Elementary: pair `d` with the label that flips the sign of the triple owning `u`
or, for the other two lines of that triple, swaps them. -/
theorem erdos_69__h4__h1 : ∀ (M P u x : ℕ), 1 ≤ u → u ≤ 3 * M →
    ∑ d ∈ Finset.univ.filter (fun d : Fin M → Fin 6 =>
      Opn.E69.shift M P d + Opn.E69.dil M P d * u = x), Opn.E69.sign M d = 0 := by
  sorry

/-- h4b (what is left): on an admissible base the signed combination is `2^(-3M)` times the
signed combination of the tails started `3M` steps later. -/
theorem erdos_69__h4__h2 : ∀ (M P n₀ t : ℕ), Opn.E69.Admissible M P n₀ →
    Opn.E69.signedTail M P n₀ t = (1 / 2 ^ (3 * M) : ℝ) *
      ∑ d : Fin M → Fin 6, (Opn.E69.sign M d : ℝ) * Opn.E69.tail (Opn.E69.dil M P d)
        (Opn.E69.start M P n₀ d + Opn.E69.step M P d * t + 3 * M) := by
  sorry

/-- Sanity, by evaluation: the 36 lines of `M = 2` cancel at every depth `u = 1..6`
(a point at depth `u` is `P# (σ + (1 + g) u) + u`, so it is determined by `σ + (1 + g) u`). -/
example : ∀ u ∈ Finset.Icc 1 6, ∀ d₀ : Fin 2 → Fin 6,
    ∑ d ∈ Finset.univ.filter (fun d : Fin 2 → Fin 6 =>
      Opn.E69.sIndex 2 d + (1 + Opn.E69.gIndex 2 d) * u
        = Opn.E69.sIndex 2 d₀ + (1 + Opn.E69.gIndex 2 d₀) * u), Opn.E69.sign 2 d = 0 := by
  decide +kernel
