import OpnGate.Hazards

/-! `off-by-one-range` (F02-R2): a range or comparison boundary adjacent to an explicit literal.
`n < 10` versus `n ≤ 10`, `Finset.range (n + 1)` versus `Finset.range n`: the literal is where a
statement is most often off by one. Flags `<`, `≤`, `>`, `≥` with a non-zero literal on either
side (`0 < n` is the positivity idiom, not a boundary), and any `range`/`Ico`/`Icc`/`Ioc`/`Ioo`
application (`Finset`, `Set`, `List`, `Array`, `Nat`, `Multiset`) whose argument is a literal or
`_ ± literal`. -/
open Lean Meta

namespace OpnGate.Hazards

def isNonzeroLit (e : Expr) : Bool := (natLit? e).any (· != 0)

def isLitAdjusted (e : Expr) : Bool :=
  (natLit? e).isSome
    || (match binOp? e ``HAdd.hAdd with
        | some (_, a, b) => (natLit? a).isSome || (natLit? b).isSome
        | none => false)
    || (match binOp? e ``HSub.hSub with
        | some (_, _, b) => (natLit? b).isSome
        | none => false)

def rangeHeads : List String := ["range", "Ico", "Icc", "Ioc", "Ioo", "Ici", "Iic", "Ioi", "Iio"]

def isRangeConst (n : Name) : Bool :=
  match n with
  | .str p s =>
    rangeHeads.contains s
      && [`Finset, `Set, `List, `Array, `Nat, `Multiset, `Int].contains p
  | _ => false

def offByOneRange : Checker where
  id := "off-by-one-range"
  describe := "a range or ≤/< boundary adjacent to an explicit literal"
  visit e := do
    for op in [``LT.lt, ``LE.le, ``GT.gt, ``GE.ge] do
      if e.isAppOfArity op 4 then
        let args := e.getAppArgs
        if isNonzeroLit args[2]! || isNonzeroLit args[3]! then
          return some { message := "comparison against an explicit literal: check whether the boundary is inclusive or exclusive" }
        return none
    if isRangeConst (headName e) && (← fullyApplied e) then
      if e.getAppArgs.any isLitAdjusted then
        return some { message := s!"{headName e} with a literal-adjusted bound: check whether the endpoint is included" }
    return none

end OpnGate.Hazards
