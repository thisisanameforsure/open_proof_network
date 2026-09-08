import OpnGate.Hazards
import OpnGate.Hazards.DivZero

/-! `int-trunc` (F02-R2): a coercion or division on ℤ that truncates. `Int.toNat` sends every
negative integer to `0`; `/` and `%` on ℤ round (toward −∞ for `Int.ediv`, toward zero for
`Int.tdiv`), so `z / 2 * 2 = z` is false for odd `z` and a statement can quietly range over the
rounded values. Division on ℕ is `div-zero`'s business and is not flagged here. -/
open Lean Meta

namespace OpnGate.Hazards

def intTrunc : Checker where
  id := "int-trunc"
  describe := "a coercion or division on ℤ that truncates (Int.toNat, / and % on ℤ)"
  visit e := do
    if e.isAppOfArity ``Int.toNat 1 then
      return some { message := "Int.toNat truncates every negative integer to 0" }
    match divisor? e with
    | some (kind, _) =>
      let onInt :=
        (match binOp? e ``HDiv.hDiv with | some (ty, _, _) => isInt ty | none => false)
        || (match binOp? e ``HMod.hMod with | some (ty, _, _) => isInt ty | none => false)
        || (e.isAppOfArity ``Div.div 4 && isInt e.getAppArgs[0]!)
        || (e.isAppOfArity ``Mod.mod 4 && isInt e.getAppArgs[0]!)
        || ((headName e).getPrefix == `Int)
      if onInt then
        return some { message := s!"{kind} on ℤ rounds: the result is not the rational quotient" }
      return none
    | none => return none

end OpnGate.Hazards
