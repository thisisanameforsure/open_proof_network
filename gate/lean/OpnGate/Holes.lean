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
  /-- The hole's type as written, in the context of the binders it sits under. -/
  type : String
  /-- The same obligation closed over those binders — a standalone statement, which is what a
  child node needs (D-29): a hole typed `q` under `∀ p q, p ∧ q → q ∧ p` becomes
  `∀ (p q : Prop), p ∧ q → q`. Without this a child's `Statement.lean` would not elaborate. -/
  closed_type : String
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

/-- Is `t` the goal restated? Compared against the conclusion in the theorem's own binder context
and against the whole statement, and the closed form against the statement too, because all three
are the same evasion wearing different numbers of binders. -/
private def restatesGoal (goal stmt t closed : Expr) : MetaM Bool := do
  try
    for (a, b) in #[(t, goal), (t, stmt), (closed, stmt)] do
      if ← withReducible (isDefEq a b) then return true
    for (a, b) in #[(t, goal), (t, stmt), (closed, stmt)] do
      if ← isDefEq a b then return true
    return false
  catch _ => return false

private partial def scan (goal stmt : Expr) (binders : Array Expr) (e : Expr) (acc : Acc)
    : MetaM Acc := do
  let e := e.consumeMData
  if isSorry e then
    return { acc with unnamed := acc.unnamed + 1 }
  match e with
  | .letE n t v b _ =>
    if isSorry v then
      let closed ← instantiateMVars (← mkForallFVars binders t)
      let hole : Hole := {
        name := n.toString,
        type := toString (← ppExpr t),
        closed_type := toString (← ppExpr closed),
        defeq_goal := ← restatesGoal goal stmt t closed }
      let acc := { acc with holes := acc.holes.push hole }
      withLocalDeclD n t fun x => scan goal stmt (binders.push x) (b.instantiate1 x) acc
    else
      let acc ← scan goal stmt binders t acc
      let acc ← scan goal stmt binders v acc
      withLetDecl n t v fun x => scan goal stmt (binders.push x) (b.instantiate1 x) acc
  | .app f a =>
    let acc ← scan goal stmt binders f acc
    scan goal stmt binders a acc
  | .lam n t b bi =>
    let acc ← scan goal stmt binders t acc
    withLocalDecl n bi t fun x => scan goal stmt (binders.push x) (b.instantiate1 x) acc
  | .forallE n t b bi =>
    let acc ← scan goal stmt binders t acc
    withLocalDecl n bi t fun x => scan goal stmt (binders.push x) (b.instantiate1 x) acc
  | .proj _ _ s => scan goal stmt binders s acc
  | _ => return acc

/-- Every hole in `value`, a proof of `stmt`. -/
def holeReport (stmt value : Expr) : MetaM HoleReport := do
  lambdaTelescope value fun xs body => do
    let goal ← inferType body
    let acc ← scan goal stmt xs body {}
    return { holes := acc.holes, unnamed := acc.unnamed, body_is_hole := isSorry body }

end OpnGate
