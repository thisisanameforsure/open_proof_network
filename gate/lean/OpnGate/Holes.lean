import Lean
import OpnGate.WitnessType

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

A hole may also restate a statement the target already has (F07-T7): the 2026-09-13 live skeleton's
first hole was the tutorial's own theorem. Each hole therefore names the first sibling statement
its closed type is definitionally equal to, and the post-merge job makes that a dependency edge
instead of a new node.
-/
open Lean Elab Meta

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
  /-- The node of the target whose statement the closed type is, definitionally, if any
  (F07-T7). -/
  defeq_sibling : Option String := none
  /-- Whether `closed_type`, read back as Lean source, elaborates to this same obligation
  (F07-R19). A type printed without its coercion ascriptions can elaborate at another type
  entirely and say nothing about the hole: `(ω n : ℝ) / 2 ^ n` prints as `↑(ω n) / 2 ^ n`, which
  reads back over `ℕ`, where the division truncates (found live on erdos-69, 2026-09-17). The
  post-merge writer refuses to make a child from a hole that reports `false`, because such a
  child's `Statement.lean` would not be the obligation the assembly discharged. -/
  closed_roundtrip : Bool := true
  /-- Step 7's expected witness type for the node this hole becomes (F07-R21): exists over the
  closed obligation's variables of the conjunction of its hypotheses, the same function step 7
  calls. Every hole's slot used to be written as `theorem witness : True`, whatever its
  hypotheses, so the one file that names the obligation named the wrong one (found by an outside
  contributor on erdos-69, 2026-09-18). Reported only when the printed text reads back to the
  same type, for the reason `closed_roundtrip` exists; otherwise absent, and the slot claims
  nothing. -/
  expected_witness : Option String := none

/-- Written by hand rather than derived: a derived instance omits an absent `Option` field, and
the report says `null` so a reader can tell "no sibling" from an extractor that never asked. -/
instance : ToJson Hole where
  toJson h := Json.mkObj [
    ("name", Json.str h.name),
    ("type", Json.str h.type),
    ("closed_type", Json.str h.closed_type),
    ("defeq_goal", Json.bool h.defeq_goal),
    ("defeq_sibling", match h.defeq_sibling with
      | some node => Json.str node
      | none => Json.null),
    ("closed_roundtrip", Json.bool h.closed_roundtrip),
    ("expected_witness", match h.expected_witness with
      | some t => Json.str t
      | none => Json.null)]

/-- What a partial proof's body is made of. -/
structure HoleReport where
  holes : Array Hole
  /-- `sorry`s that are not the value of a `have`; each is a hole the submitter did not name. -/
  unnamed : Nat
  /-- The body is one hole and nothing else — the offload rule's second shape. -/
  body_is_hole : Bool
deriving ToJson

/-- Print `e` as source that can be elaborated back (F07-R19).

`ppExpr`'s defaults drop the information a reader needs to recover the type: a coercion prints as
a bare `↑` and a numeral prints without its type, so `(ω n : ℝ) / 2 ^ n` comes out as
`↑(ω n) / 2 ^ n` and reads back over `ℕ`. Both options were checked against Lean 4.33.1 rather
than assumed: with them the three obligations that failed round-trip true. -/
def ppRoundTrippable (e : Expr) : MetaM String :=
  withOptions (fun o => (o.setBool `pp.coercions.types true).setBool `pp.numericTypes true) do
    return toString (← ppExpr e)

/-- Does `src`, elaborated as a type, mean the same as `e`? The guard on what the post-merge
writer may put in a child's `Statement.lean`: anything that fails here would publish a node that
is not the hole. A `src` that does not parse or elaborate answers `false` rather than throwing. -/
def reElaboratesTo (src : String) (e : Expr) : TermElabM Bool := do
  try
    let stx ← ofExcept (Parser.runParserCategory (← getEnv) `term src)
    let e2 ← Term.elabType stx
    Term.synthesizeSyntheticMVarsNoPostponing
    isDefEq e (← instantiateMVars e2)
  catch _ => pure false

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

/-- The first sibling, in the order given, whose statement the closed hole is (F07-T7). The same
two transparencies as the goal check; a comparison that throws is not a match. -/
private def restatesSibling (siblings : Array (String × Expr)) (closed : Expr)
    : MetaM (Option String) := do
  for (node, ty) in siblings do
    let same ← try withReducible (isDefEq closed ty) <||> isDefEq closed ty
      catch _ => pure false
    if same then return some node
  return none

private partial def scan (goal stmt : Expr) (siblings : Array (String × Expr))
    (binders : Array Expr) (e : Expr) (acc : Acc) : TermElabM Acc := do
  let e := e.consumeMData
  if isSorry e then
    return { acc with unnamed := acc.unnamed + 1 }
  match e with
  | .letE n t v b _ =>
    if isSorry v then
      let closed ← instantiateMVars (← mkForallFVars binders t)
      let printed ← ppRoundTrippable closed
      let expected ← expectedWitnessType closed
      let expectedPrinted ← ppRoundTrippable expected
      let expectedOk ← reElaboratesTo expectedPrinted expected
      let hole : Hole := {
        name := n.toString,
        type := ← ppRoundTrippable t,
        closed_type := printed,
        defeq_goal := ← restatesGoal goal stmt t closed,
        defeq_sibling := ← restatesSibling siblings closed,
        closed_roundtrip := ← reElaboratesTo printed closed,
        expected_witness := if expectedOk then some expectedPrinted else none }
      let acc := { acc with holes := acc.holes.push hole }
      withLocalDeclD n t fun x => scan goal stmt siblings (binders.push x) (b.instantiate1 x) acc
    else
      let acc ← scan goal stmt siblings binders t acc
      let acc ← scan goal stmt siblings binders v acc
      withLetDecl n t v fun x => scan goal stmt siblings (binders.push x) (b.instantiate1 x) acc
  | .app f a =>
    let acc ← scan goal stmt siblings binders f acc
    scan goal stmt siblings binders a acc
  | .lam n t b bi =>
    let acc ← scan goal stmt siblings binders t acc
    withLocalDecl n bi t fun x => scan goal stmt siblings (binders.push x) (b.instantiate1 x) acc
  | .forallE n t b bi =>
    let acc ← scan goal stmt siblings binders t acc
    withLocalDecl n bi t fun x => scan goal stmt siblings (binders.push x) (b.instantiate1 x) acc
  | .proj _ _ s => scan goal stmt siblings binders s acc
  | _ => return acc

/-- Every hole in `value`, a proof of `stmt`; each named against `siblings`, the target's other
statements as `(node id, type)` (F07-T7; empty when the caller staged none). -/
def holeReport (stmt value : Expr) (siblings : Array (String × Expr) := #[])
    : TermElabM HoleReport := do
  lambdaTelescope value fun xs body => do
    let goal ← inferType body
    let acc ← scan goal stmt siblings xs body {}
    return { holes := acc.holes, unnamed := acc.unnamed, body_is_hole := isSorry body }

end OpnGate
