import Defs.Divides

/-! A prime, over the graph's own divisibility: at least 2, with only the trivial divisors. -/

def Opn.IsPrime (p : Nat) : Prop := 2 ≤ p ∧ ∀ d : Nat, Opn.Divides d p → d = 1 ∨ d = p
