import Mathlib
import Defs.Construction

/-- h4c (something survives): for even `M`, at every depth `u > 3M` the line labelled `2…2`
(slope digit 0 in every triple, sign `+1`) is alone on its point among the lines at that depth.
Proof: in each triple, `sDigit + gDigit · u` is minimised exactly at `k = 2` once `u > 3M`; the
bound is sharp (at `u = 3r + 4`, `r` even, lines 1 and 2 of triple `r` meet). -/
theorem erdos_69__h4__h3 : ∀ (M P u : ℕ), Even M → 3 * M + 1 ≤ u → ∀ d : Fin M → Fin 6,
    Opn.E69.shift M P d + Opn.E69.dil M P d * u
      = Opn.E69.shift M P (fun _ => 2) + Opn.E69.dil M P (fun _ => 2) * u → d = fun _ => 2 := by
  intro M P u hM hu d hd
  have tw : ∀ r : ℕ, r < M → ∀ k : Fin 6,
      Opn.E69.sDigit r 2 + Opn.E69.gDigit r 2 * u ≤ Opn.E69.sDigit r k + Opn.E69.gDigit r k * u ∧
      (Opn.E69.sDigit r 2 + Opn.E69.gDigit r 2 * u = Opn.E69.sDigit r k + Opn.E69.gDigit r k * u
        → k = 2) := by
    intro r hr k
    obtain ⟨N, rfl⟩ := hM
    unfold Opn.E69.sDigit Opn.E69.gDigit
    rcases Nat.mod_two_eq_zero_or_one r with h | h
    · fin_cases k <;> simp [h] <;> omega
    · fin_cases k <;> simp [h] <;> omega
  have hF : ∀ e : Fin M → Fin 6, Opn.E69.sIndex M e + Opn.E69.gIndex M e * u
      = ∑ r : Fin M, 7 ^ (r : ℕ) * (Opn.E69.sDigit r (e r) + Opn.E69.gDigit r (e r) * u) := by
    intro e
    unfold Opn.E69.sIndex Opn.E69.gIndex
    rw [Finset.sum_mul, ← Finset.sum_add_distrib]
    exact Finset.sum_congr rfl fun r _ => by ring
  have hkey : Opn.E69.sIndex M d + Opn.E69.gIndex M d * u
      = Opn.E69.sIndex M (fun _ => 2) + Opn.E69.gIndex M (fun _ => 2) * u := by
    have e : ∀ s g : ℕ, primorial P * s + (1 + primorial P * (1 + g)) * u
        = primorial P * (s + g * u) + (u + primorial P * u) := by intros; ring
    unfold Opn.E69.shift Opn.E69.dil at hd
    rw [e, e] at hd
    exact Nat.eq_of_mul_eq_mul_left (primorial_pos P) (Nat.add_right_cancel hd)
  rw [hF d, hF (fun _ => 2)] at hkey
  have hle : ∀ r ∈ (Finset.univ : Finset (Fin M)),
      7 ^ (r : ℕ) * (Opn.E69.sDigit r 2 + Opn.E69.gDigit r 2 * u)
        ≤ 7 ^ (r : ℕ) * (Opn.E69.sDigit r (d r) + Opn.E69.gDigit r (d r) * u) :=
    fun r _ => Nat.mul_le_mul_left _ (tw r r.isLt (d r)).1
  have heq := (Finset.sum_eq_sum_iff_of_le hle).mp hkey.symm
  funext r
  have h1 := heq r (Finset.mem_univ r)
  exact (tw r r.isLt (d r)).2 (Nat.eq_of_mul_eq_mul_left (by positivity) h1)
