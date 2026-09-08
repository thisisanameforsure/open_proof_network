import OpnGate.Hazards

/-! `unused-binder` (F02-R2): a universally quantified variable nothing depends on. A statement
`∀ (n m : ℕ), n = n` says nothing about `m`, which usually means a hypothesis was meant to
mention it. Only data binders count: an unused hypothesis (a `Prop` binder) is an implication
whose premise happens to be idle, and instance binders are used through instance resolution, not
by name. The location is the binder's name (F02-Q4), since the ∀ itself may span the statement. -/
open Lean Meta

namespace OpnGate.Hazards

def unusedBinder : Checker where
  id := "unused-binder"
  describe := "a universally quantified variable nothing depends on"
  visit e := do
    match e with
    | .forallE n t b bi =>
      if bi.isInstImplicit || b.hasLooseBVar 0 then return none
      if ← isProp t then return none
      return some {
        message := s!"binder {n} is quantified but nothing after it mentions it"
        location := some n.toString }
    | _ => return none

end OpnGate.Hazards
