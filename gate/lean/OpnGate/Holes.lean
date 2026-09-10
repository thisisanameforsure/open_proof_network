import Lean

/-!
Hole extraction for D-12's partial proofs (F07-R5, R6).

A partial proof is an assembly that typechecks modulo named holes: `have h : T := sorry` inside
the body of `theorem <decl> : S`. Each such hole is a candidate child node (D-29), so the gate
has to say exactly what they are — a name and a type — and refuse the two shapes that are fake
progress rather than decomposition (D-12's offload rule):

* a hole whose type is the goal itself, which is the goal restated under a new name;
* an assembly that is nothing but a hole.

Shape, checked against Lean 4.33 rather than assumed: `have x : T := v; b` elaborates to
`Expr.letE x T v b`, and `sorry` to an application headed by `sorryAx`. A `sorry` that is not the
value of such a binder is counted as unnamed: it is a hole nobody named, and a child node cannot
be made from it.
-/
open Lean Meta

namespace OpnGate

/-- One `have`-bound hole in a partial proof. -/
structure Hole where
  name : String
  type : String
  /-- The offload rule's question: is this hole the node's own goal wearing a new name? -/
  defeq_goal : Bool
deriving ToJson

/-- What a partial proof's body is made of. -/
structure HoleReport where
  holes : Array Hole
  /-- `sorry`s that are not the value of a `have`; each is a hole the submitter did not name. -/
  unnamed : Nat
  /-- The body is one hole and nothing else — the offload rule's second shape. -/
  body_is_hole : Bool
deriving ToJson

/-- Is `e` an application of `sorryAx`? (`sorry` elaborates to `sorryAx (Name → α) _ <tag>`.) -/
def isSorry (e : Expr) : Bool :=
  e.consumeMData.getAppFn.isConstOf ``sorryAx

private structure Acc where
  holes : Array Hole := #[]
  unnamed : Nat := 0

/-- Is `t` the goal restated? Compared against both the conclusion in the theorem's own binder
context and the whole statement type, because either is the same evasion. -/
private def restatesGoal (goal stmt t : Expr) : MetaM Bool := do
  try
    if ← withReducible (isDefEq t goal) then return true
    if ← withReducible (isDefEq t stmt) then return true
    if ← isDefEq t goal then return true
    isDefEq t stmt
  catch _ => return false

private partial def scan (goal stmt : Expr) (e : Expr) (acc : Acc) : MetaM Acc := do
  let e := e.consumeMData
  if isSorry e then
    return { acc with unnamed := acc.unnamed + 1 }
  match e with
  | .letE n t v b _ =>
    if isSorry v then
      let hole : Hole := {
        name := n.toString, type := toString (← ppExpr t),
        defeq_goal := ← restatesGoal goal stmt t }
      let acc := { acc with holes := acc.holes.push hole }
      withLocalDeclD n t fun x => scan goal stmt (b.instantiate1 x) acc
    else
      let acc ← scan goal stmt t acc
      let acc ← scan goal stmt v acc
      withLetDecl n t v fun x => scan goal stmt (b.instantiate1 x) acc
  | .app f a =>
    let acc ← scan goal stmt f acc
    scan goal stmt a acc
  | .lam n t b bi =>
    let acc ← scan goal stmt t acc
    withLocalDecl n bi t fun x => scan goal stmt (b.instantiate1 x) acc
  | .forallE n t b bi =>
    let acc ← scan goal stmt t acc
    withLocalDecl n bi t fun x => scan goal stmt (b.instantiate1 x) acc
  | .proj _ _ s => scan goal stmt s acc
  | _ => return acc

/-- Every hole in `value`, a proof of `stmt`. -/
def holeReport (stmt value : Expr) : MetaM HoleReport := do
  lambdaTelescope value fun _xs body => do
    let goal ← inferType body
    let acc ← scan goal stmt body {}
    return { holes := acc.holes, unnamed := acc.unnamed, body_is_hole := isSorry body }

end OpnGate
