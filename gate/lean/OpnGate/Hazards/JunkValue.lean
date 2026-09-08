import OpnGate.Hazards
import OpnGate.Hazards.DivZero

/-! `junk-value` (F02-R2): a total function applied where its result is a default, not a value.
Flags `Nat.pred x` unless `x` is syntactically non-zero; any panicking accessor (a constant whose
last name component ends in `!`, e.g. `List.head!`, `Option.get!`, `Array.get!`); and
`Real.sqrt x` / `Real.log x` unless `x` is syntactically non-negative — a literal, a cast from ℕ,
an absolute value or an even power. Mathlib names are matched by name only (the package is
Lean-core-only), so they fire on a Mathlib-pinned graph without the package importing it. -/
open Lean Meta

namespace OpnGate.Hazards

def syntacticallyNonneg (e : Expr) : Bool :=
  (natLit? e).isSome
    || e.isAppOfArity ``Nat.cast 3
    || e.isAppOfArity ``NatCast.natCast 3
    || e.isAppOf `abs
    || (match binOp? e ``HPow.hPow with
        | some (_, _, k) => (natLit? k).any (· % 2 == 0)
        | none => false)

def isPanicking (n : Name) : Bool :=
  match n with
  | .str _ s => s.endsWith "!"
  | _ => false

def junkValue : Checker where
  id := "junk-value"
  describe := "a total function applied outside its meaningful domain (Nat.pred 0, head!, sqrt of a negative)"
  visit e := do
    if e.isAppOfArity ``Nat.pred 1 then
      if syntacticallyNonzero e.appArg! then return none
      return some { message := "Nat.pred 0 = 0: the predecessor of a possibly-zero argument is a junk value" }
    if isPanicking (headName e) && (← fullyApplied e) then
      return some { message := s!"{headName e} returns a default value where it would panic; the statement may hold on the default" }
    if e.isAppOfArity `Real.sqrt 1 || e.isAppOfArity `Real.log 1 then
      if syntacticallyNonneg e.appArg! then return none
      return some { message := s!"{headName e} of a possibly-negative argument is a junk value (0)" }
    return none

end OpnGate.Hazards
