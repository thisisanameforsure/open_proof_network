import Mathlib
import Defs.Construction

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

