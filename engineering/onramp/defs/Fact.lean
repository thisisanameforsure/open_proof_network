/-! The factorial, by recursion; `Nat.factorial`'s lemmas do not apply to it by name. -/

def Opn.fact : Nat → Nat
  | 0 => 1
  | n + 1 => (n + 1) * Opn.fact n
