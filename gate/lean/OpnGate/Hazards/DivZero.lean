import OpnGate.Hazards

/-! `div-zero` (F02-R2): a division or modulo whose divisor is not syntactically non-zero. Lean's
`/` and `%` are total — `a / 0 = 0` on ℕ, ℤ and every division ring — so a statement dividing by a
variable can hold vacuously at zero. A divisor is syntactically non-zero when it is a non-zero
literal, `Nat.succ _`, `_ + k` or `k ^ _` on ℕ with `k` non-zero, `-k` for a non-zero literal `k`,
or `Int.negSucc _`. A hypothesis `b ≠ 0` in scope does not count (Q3: conservative v1 contract). -/
open Lean Meta

namespace OpnGate.Hazards

partial def syntacticallyNonzero (e : Expr) : Bool :=
  match natLit? e with
  | some n => n != 0
  | none =>
    e.isAppOfArity ``Nat.succ 1
    || e.isAppOfArity ``Int.negSucc 1
    || (match binOp? e ``HAdd.hAdd with
        | some (ty, a, b) => isNat ty && (syntacticallyNonzero a || syntacticallyNonzero b)
        | none => false)
    || (match binOp? e ``HPow.hPow with
        | some (ty, a, _) => isNat ty && syntacticallyNonzero a
        | none => false)
    || (e.isAppOfArity ``Neg.neg 3 && (natLit? e.getAppArgs[2]!).any (· != 0))

/-- The divisor of `e` when `e` is a division or modulo, else `none`. -/
def divisor? (e : Expr) : Option (String × Expr) :=
  if let some (_, _, b) := binOp? e ``HDiv.hDiv then some ("division", b)
  else if let some (_, _, b) := binOp? e ``HMod.hMod then some ("modulo", b)
  else if e.isAppOfArity ``Div.div 4 then some ("division", e.getAppArgs[3]!)
  else if e.isAppOfArity ``Mod.mod 4 then some ("modulo", e.getAppArgs[3]!)
  else
    let named : List (Name × String) := [
      (``Nat.div, "division"), (``Nat.mod, "modulo"),
      (``Int.ediv, "division"), (``Int.tdiv, "division"), (``Int.fdiv, "division"),
      (``Int.bdiv, "division"),
      (``Int.emod, "modulo"), (``Int.tmod, "modulo"), (``Int.fmod, "modulo"),
      (``Int.bmod, "modulo")]
    named.findSome? fun (n, kind) =>
      if e.isAppOfArity n 2 then some (kind, e.getAppArgs[1]!) else none

def divZero : Checker where
  id := "div-zero"
  describe := "division or modulo whose divisor is not syntactically non-zero"
  visit e := do
    match divisor? e with
    | some (kind, d) =>
      if syntacticallyNonzero d then return none
      return some { message := s!"{kind} by a divisor that is not syntactically non-zero: Lean's / and % are total and give a junk value at 0" }
    | none => return none

end OpnGate.Hazards
