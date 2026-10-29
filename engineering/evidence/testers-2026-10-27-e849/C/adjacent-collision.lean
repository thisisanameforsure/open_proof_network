import Mathlib

open Nat

/-! Elementary pieces of B's h_adjacent (--h2--h1--h2, Tovey/Lind), for A's possible third level (agent C).
E1: an adjacent collision C(m+1,k) = C(m,k+1) (k ≤ m) is the quadratic (m+1)(k+1) = (m−k)(m+1−k).
E2: with u = m − k that is u² = u k + (k+1)², i.e. the Pell equation (5k+4)² − 5(2u − k)² = −4.
The deep half (every solution of X² − 5Y² = −4 is a Lucas/Fibonacci pair, then the Lind indices) is Tovey's. -/

/-- E1. -/
theorem e849_adjacent_iff (m k : ℕ) (hk : k ≤ m) :
    (m + 1).choose k = m.choose (k + 1) ↔ (m + 1) * (k + 1) = (m - k) * (m + 1 - k) := by
  have h1 := Nat.choose_mul_succ_eq m k          -- m.choose k * (m + 1) = (m+1).choose k * (m + 1 - k)
  have h2 := Nat.choose_succ_right_eq m k        -- m.choose (k+1) * (k+1) = m.choose k * (m - k)
  have hpos : 0 < m.choose k := Nat.choose_pos hk
  constructor
  · intro h
    -- multiply both identities to isolate m.choose k
    have e : m.choose k * ((m + 1) * (k + 1)) = m.choose k * ((m - k) * (m + 1 - k)) := by
      calc m.choose k * ((m + 1) * (k + 1)) = (m.choose k * (m + 1)) * (k + 1) := by ring
        _ = ((m + 1).choose k * (m + 1 - k)) * (k + 1) := by rw [h1]
        _ = (m.choose (k + 1) * (k + 1)) * (m + 1 - k) := by rw [h]; ring
        _ = (m.choose k * (m - k)) * (m + 1 - k) := by rw [h2]
        _ = m.choose k * ((m - k) * (m + 1 - k)) := by ring
    exact Nat.eq_of_mul_eq_mul_left hpos e
  · intro h
    have hk1 : 0 < m + 1 - k := by omega
    have e : (m + 1).choose k * ((m + 1 - k) * (k + 1)) = m.choose (k + 1) * ((m + 1 - k) * (k + 1)) := by
      calc (m + 1).choose k * ((m + 1 - k) * (k + 1)) = ((m + 1).choose k * (m + 1 - k)) * (k + 1) := by ring
        _ = (m.choose k * (m + 1)) * (k + 1) := by rw [h1]
        _ = m.choose k * ((m + 1) * (k + 1)) := by ring
        _ = m.choose k * ((m - k) * (m + 1 - k)) := by rw [h]
        _ = (m.choose k * (m - k)) * (m + 1 - k) := by ring
        _ = (m.choose (k + 1) * (k + 1)) * (m + 1 - k) := by rw [h2]
        _ = m.choose (k + 1) * ((m + 1 - k) * (k + 1)) := by ring
    exact Nat.eq_of_mul_eq_mul_right (by positivity) e

/-- E2, in ℤ: the quadratic is the Pell equation `(5k+4)² − 5(2u − k)² = −4` with `u = m − k`. -/
theorem e849_adjacent_pell (m k : ℕ) (hk : k ≤ m) (h : (m + 1) * (k + 1) = (m - k) * (m + 1 - k)) :
    ((5 * k + 4 : ℤ)) ^ 2 - 5 * (2 * ((m : ℤ) - k) - k) ^ 2 = -4 := by
  obtain ⟨u, rfl⟩ : ∃ u, m = u + k := ⟨m - k, by omega⟩
  have h' : (u + k + 1) * (k + 1) = u * (u + 1) := by
    have e1 : u + k - k = u := by omega
    have e2 : u + k + 1 - k = u + 1 := by omega
    rw [e1, e2] at h; exact h
  have hz : ((u : ℤ) + k + 1) * (k + 1) = u * (u + 1) := by exact_mod_cast h'
  push_cast
  nlinarith [hz]

/-- The Lind family satisfies the quadratic (i = 1, 2 by computation; the general case is a Fibonacci identity). -/
example : (15 : ℕ) * 6 = 9 * 10 ∧ (104 : ℕ) * 40 = 64 * 65 := by norm_num
