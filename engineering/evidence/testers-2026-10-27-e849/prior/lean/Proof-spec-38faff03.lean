import Mathlib
import Nodes.«spec-38faff03».Context

open Nat

private theorem step_lt (n k : ℕ) (h : 2 * (k + 1) ≤ n) : choose n k < choose n (k + 1) := by
  have e := Nat.choose_succ_right_eq n k
  have hp : 0 < choose n k := Nat.choose_pos (by omega)
  have hk : k + 1 < n - k := by omega
  by_contra hc
  push_neg at hc
  have : choose n k * (n - k) ≤ choose n k * (k + 1) := by
    calc choose n k * (n - k) = choose n (k + 1) * (k + 1) := e.symm
      _ ≤ choose n k * (k + 1) := Nat.mul_le_mul_right _ hc
  have := Nat.le_of_mul_le_mul_left this hp
  omega

private theorem mono_lt (n : ℕ) : ∀ j i : ℕ, i < j → 2 * j ≤ n → choose n i < choose n j := by
  intro j
  induction j with
  | zero => intro i h; omega
  | succ j ih =>
    intro i hij hj
    have hs := step_lt n j hj
    rcases Nat.lt_succ_iff_lt_or_eq.mp hij with h | h
    · exact lt_trans (ih i h (by omega)) hs
    · subst h; exact hs

/-- Erdős 849, structure: every row that holds the value `a` at some `1 ≤ k ≤ n/2` satisfies
`2 ≤ n ≤ a`, because `C(n, k) ≥ C(n, 1) = n` there. So each solution set is finite, and a
search for the rows holding `a` need only look at `n ≤ a`. -/
theorem Opn.erdos_849_rows_le : ∀ a : ℕ,
    {n : ℕ | ∃ k ≥ 1, 2 * k ≤ n ∧ choose n k = a} ⊆ Set.Icc 2 a := by
  rintro a n ⟨k, hk, hkn, rfl⟩
  refine ⟨by omega, ?_⟩
  rcases Nat.lt_or_ge 1 k with h | h
  · have := mono_lt n k 1 h hkn
    rw [Nat.choose_one_right] at this
    omega
  · have : k = 1 := by omega
    subst this
    rw [Nat.choose_one_right]
