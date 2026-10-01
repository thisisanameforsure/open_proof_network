import OpnGate.Hazards

/-! `nat-div` (F02-T9): division on ℕ in the statement. `a / b` on ℕ is the floor of the quotient
— `n / 2 * 2 = n` fails for odd `n` — and a quotient or sum written over ℕ for want of a `: ℝ`
ascription computes in that arithmetic while reading as the real one; the gate-written holes of
2026-09-17 fell exactly there, and `int-trunc` flags the integers only (two testers, 2026-09-27).
Flags every `HDiv.hDiv ℕ ℕ ℕ _ a b`, `Div.div ℕ _ a b` and `Nat.div a b`. `div-zero` asks a
different question (the divisor) of the same subterm and may fire beside it. -/
open Lean Meta

namespace OpnGate.Hazards

def natDiv : Checker where
  id := "nat-div"
  describe := "division on ℕ in the statement (the floor of the quotient, not the rational one)"
  visit e := do
    let onNat :=
      (e.isAppOfArity ``HDiv.hDiv 6 && isNat e.getAppArgs[0]! && isNat e.getAppArgs[1]!)
      || (e.isAppOfArity ``Div.div 4 && isNat e.getAppArgs[0]!)
      || e.isAppOfArity ``Nat.div 2
    if onNat then
      return some { message := "natural-number division truncates: a / b is the floor of the quotient, so a / b * b = a fails unless b divides a; a quotient meant over ℚ or ℝ needs its ascription" }
    return none

end OpnGate.Hazards
