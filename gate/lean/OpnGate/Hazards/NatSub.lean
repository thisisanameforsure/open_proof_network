import OpnGate.Hazards

/-! `nat-sub` (F02-R2): subtraction on ℕ in the statement. `a - b` is `0` whenever `b ≥ a`, so a
statement can be true for the wrong reason. Flags every `HSub.hSub ℕ ℕ ℕ _ a b` and `Nat.sub a b`. -/
open Lean Meta

namespace OpnGate.Hazards

def natSub : Checker where
  id := "nat-sub"
  describe := "subtraction on ℕ in the statement (truncates at 0)"
  visit e := do
    if let some (ty, _, _) := binOp? e ``HSub.hSub then
      if isNat ty then
        return some "subtraction on ℕ truncates at 0: a - b is 0 whenever b ≥ a"
    if e.isAppOfArity ``Nat.sub 2 then
      return some "subtraction on ℕ truncates at 0: Nat.sub a b is 0 whenever b ≥ a"
    return none

end OpnGate.Hazards
