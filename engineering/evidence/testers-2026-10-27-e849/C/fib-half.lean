import Mathlib

open Nat

/-! Fibonacci half of h_adjacent (agent C): the solutions reached by the step are (L_{2j+1}, F_{2j+1}),
L_{2j+1} ≡ 4 (mod 5) forces j odd, and for j = 2i+1 the Lind indices come out. -/

/-- Cassini for even index: F_{2i}² + F_{2i}F_{2i+1} − F_{2i+1}² = −1. -/
private theorem e849_cassini (i : ℕ) :
    ((fib (2 * i) : ℤ)) ^ 2 + (fib (2 * i) : ℤ) * fib (2 * i + 1) - ((fib (2 * i + 1) : ℤ)) ^ 2 = -1 := by
  induction i with
  | zero => simp
  | succ i ih =>
    have h1 : fib (2 * (i + 1)) = fib (2 * i) + fib (2 * i + 1) := by
      rw [show 2 * (i + 1) = 2 * i + 2 by ring, Nat.fib_add_two]
    have h2 : fib (2 * (i + 1) + 1) = fib (2 * i) + 2 * fib (2 * i + 1) := by
      rw [show 2 * (i + 1) + 1 = 2 * i + 1 + 2 by ring, Nat.fib_add_two, show 2 * i + 1 + 1 = 2 * (i + 1) by ring, h1]; ring
    rw [h1, h2]; push_cast; linear_combination ih

/-- The step keeps the Lucas/Fibonacci shape: P a b := ∃ j, a = 2F_{2j+2} − F_{2j+1} ∧ b = F_{2j+1}. -/
private theorem e849_lucas_step (j : ℕ) :
    (3 * (2 * (fib (2 * j + 2) : ℤ) - fib (2 * j + 1)) + 5 * (fib (2 * j + 1) : ℤ)) / 2
        = 2 * (fib (2 * (j + 1) + 2) : ℤ) - fib (2 * (j + 1) + 1) ∧
    ((2 * (fib (2 * j + 2) : ℤ) - fib (2 * j + 1)) + 3 * (fib (2 * j + 1) : ℤ)) / 2
        = (fib (2 * (j + 1) + 1) : ℤ) := by
  have h3 : fib (2 * (j + 1) + 1) = fib (2 * j + 1) + fib (2 * j + 2) := by
    rw [show 2 * (j + 1) + 1 = 2 * j + 1 + 2 by ring, Nat.fib_add_two]
  have h4 : fib (2 * (j + 1) + 2) = fib (2 * j + 2) + fib (2 * (j + 1) + 1) := by
    rw [show 2 * (j + 1) + 2 = 2 * j + 2 + 2 by ring, Nat.fib_add_two, show 2 * j + 2 + 1 = 2 * (j + 1) + 1 by ring]
  rw [h4, h3]; push_cast; constructor <;> omega

/-- L_{2j+1} mod 5 is 1 for even j and 4 for odd j. -/
private theorem e849_lucas_mod5 (i : ℕ) :
    (2 * (fib (2 * (2 * i) + 2) : ℤ) - fib (2 * (2 * i) + 1)) % 5 = 1 ∧
    (2 * (fib (2 * (2 * i + 1) + 2) : ℤ) - fib (2 * (2 * i + 1) + 1)) % 5 = 4 := by
  induction i with
  | zero => simp [Nat.fib_add_two]
  | succ i ih =>
    -- write every index in terms of x = F_{4i}, y = F_{4i+1}
    set x : ℤ := (fib (4 * i) : ℤ) with hx
    set y : ℤ := (fib (4 * i + 1) : ℤ) with hy
    have f2 : (fib (4 * i + 2) : ℤ) = x + y := by rw [Nat.fib_add_two]; push_cast; ring
    have f3 : (fib (4 * i + 3) : ℤ) = x + 2 * y := by rw [Nat.fib_add_two]; push_cast; rw [f2]; ring
    have f4 : (fib (4 * i + 4) : ℤ) = 2 * x + 3 * y := by rw [Nat.fib_add_two]; push_cast; rw [f2, f3]; ring
    have f5 : (fib (4 * i + 5) : ℤ) = 3 * x + 5 * y := by rw [Nat.fib_add_two]; push_cast; rw [f3, f4]; ring
    have f6 : (fib (4 * i + 6) : ℤ) = 5 * x + 8 * y := by rw [Nat.fib_add_two]; push_cast; rw [f4, f5]; ring
    have f7 : (fib (4 * i + 7) : ℤ) = 8 * x + 13 * y := by rw [Nat.fib_add_two]; push_cast; rw [f5, f6]; ring
    have e1 : 2 * (2 * i) + 2 = 4 * i + 2 := by ring
    have e2 : 2 * (2 * i) + 1 = 4 * i + 1 := by ring
    have e3 : 2 * (2 * i + 1) + 2 = 4 * i + 4 := by ring
    have e4 : 2 * (2 * i + 1) + 1 = 4 * i + 3 := by ring
    have e5 : 2 * (2 * (i + 1)) + 2 = 4 * i + 6 := by ring
    have e6 : 2 * (2 * (i + 1)) + 1 = 4 * i + 5 := by ring
    have e7 : 2 * (2 * (i + 1) + 1) + 2 = 4 * i + 8 := by ring
    have e8 : 2 * (2 * (i + 1) + 1) + 1 = 4 * i + 7 := by ring
    have f8 : (fib (4 * i + 8) : ℤ) = 13 * x + 21 * y := by rw [Nat.fib_add_two]; push_cast; rw [f6, f7]; ring
    rw [e1, e2, e3, e4] at ih
    rw [e5, e6, e7, e8, f5, f6, f7, f8]
    rw [f2, f3, f4] at ih
    omega
