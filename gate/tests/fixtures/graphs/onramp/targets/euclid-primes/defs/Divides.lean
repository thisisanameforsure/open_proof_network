/-! Divisibility, written out rather than `Nat.dvd`, so Mathlib's `Dvd` API does not apply to
it by name (F11-T1, R7; D-6): a bridge to `Nat.dvd` is a lemma, not a citation. -/

def Opn.Divides (a b : Nat) : Prop := ∃ c : Nat, b = a * c
