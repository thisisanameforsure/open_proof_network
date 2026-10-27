import Mathlib

open Nat

/-! A's k-ordering lemma for the --h3 assembly, self-contained (agent C, 2026-10-27).
Two left-half solutions of `C(·,·) = a` with `1 ≤ k, k'`: `n < n'` forces `k' < k`.
Paste the three `private` helpers before the partial's theorem, or inline `k_ordering`'s
proof as a `have`. No region hypothesis is needed: only `1 ≤ k'`, `2k ≤ n`, `2k' ≤ n'`. -/

private theorem e849_choose_lt_left (n n' k : ℕ) (hk : 1 ≤ k) (hkn : k ≤ n) (hnn : n < n') :
    n.choose k < n'.choose k := by
  obtain ⟨j, rfl⟩ : ∃ j, k = j + 1 := ⟨k - 1, by omega⟩
  induction n' with
  | zero => omega
  | succ p ih =>
    have step : ∀ q, j + 1 ≤ q → q.choose (j + 1) < (q + 1).choose (j + 1) := by
      intro q hq
      rw [Nat.choose_succ_succ']
      have : 0 < q.choose j := Nat.choose_pos (by omega)
      omega
    rcases Nat.lt_succ_iff_lt_or_eq.mp hnn with h | h
    · exact lt_trans (ih h) (step p (by omega))
    · subst h; exact step n hkn

private theorem e849_choose_lt_right (n j m : ℕ) (hjm : j < m) (hm : 2 * m ≤ n) :
    n.choose j < n.choose m := by
  have step : ∀ q, q < n / 2 → n.choose q < n.choose (q + 1) := by
    intro q hq
    have key := Nat.choose_succ_right_eq n q
    have hpos : 0 < n.choose q := Nat.choose_pos (by omega)
    by_contra hle
    have hle := Nat.le_of_not_lt hle
    have : n.choose (q + 1) * (q + 1) < n.choose q * (n - q) :=
      calc n.choose (q + 1) * (q + 1) ≤ n.choose q * (q + 1) := Nat.mul_le_mul_right _ hle
        _ < n.choose q * (n - q) := Nat.mul_lt_mul_of_pos_left (by omega) hpos
    omega
  induction m with
  | zero => omega
  | succ p ih =>
    rcases Nat.lt_succ_iff_lt_or_eq.mp hjm with h | h
    · exact lt_trans (ih h (by omega)) (step p (by omega))
    · subst h; exact step j (by omega)

/-- `n < n'` between two left-half solutions of the same value forces `k' < k`. -/
theorem k_ordering (a n k n' k' : ℕ) (hk' : 1 ≤ k') (hn : 2 * k ≤ n) (hn' : 2 * k' ≤ n')
    (h : n.choose k = a) (h' : n'.choose k' = a) (hnn : n < n') : k' < k := by
  rcases Nat.lt_or_ge k' k with hlt | hge
  · exact hlt
  rcases Nat.eq_or_lt_of_le hge with heq | hlt
  · -- same column: C(n,k) < C(n',k) contradicts equality
    subst heq
    have := e849_choose_lt_left n n' k hk' (by omega) hnn
    omega
  · -- k < k': C(n,k) ≤ C(n',k) < C(n',k')
    have h1 : n.choose k ≤ n'.choose k := Nat.choose_le_choose k hnn.le
    have h2 : n'.choose k < n'.choose k' := e849_choose_lt_right n' k k' hlt hn'
    omega
