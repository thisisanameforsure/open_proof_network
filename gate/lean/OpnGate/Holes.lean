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

A hole must not restate an *ancestor* either (F07-T34): a node that depends on this one, however
indirectly, is a question this one is part of the answer to, and a hole that hands it back down
closes a cycle in the statement graph. The goal check sees only this node's own goal, so each hole
also names the first ancestor, nearest first, whose statement it is — the same two transparencies —
and the gate refuses the partial (`offload-restates-ancestor`).
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
  /-- The ancestor of the node (a node that depends on it) whose statement the hole is,
  definitionally, if any (F07-T34): a cycle, which the offload rule refuses. -/
  defeq_ancestor : Option String := none
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
  /-- D-29 v3.22 (F07-T44): the indices, into `closed_type`'s leading `∀` binders, of the binders
  the assembly proved rather than left as holes. Step 7 does not ask a witness to exhibit them. -/
  proved_binders : Array Nat := #[]

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
    ("defeq_ancestor", match h.defeq_ancestor with
      | some node => Json.str node
      | none => Json.null),
    ("closed_roundtrip", Json.bool h.closed_roundtrip),
    ("expected_witness", match h.expected_witness with
      | some t => Json.str t
      | none => Json.null),
    ("proved_binders", toJson h.proved_binders)]

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
than assumed: with them the three obligations that failed round-trip true.

F07-T30: a binder under `∃` prints without its type (`∃ N k m, …`), and one that the body uses
only through a coercion cannot be recovered from it, so the text read back as a different type
(found live 2026-09-21 on `erdos-69`). `pp.funBinderTypes` prints `∃ (m : ℤ), …`; probed at
4.33.1, where `pp.binderTypes` does not reach an `∃` binder. It also gives an unused binder a
type, which a witness slot written from this text needs in order to elaborate at all. -/
def ppRoundTrippable (e : Expr) : MetaM String :=
  withOptions (fun o =>
      ((o.setBool `pp.coercions.types true).setBool `pp.numericTypes true).setBool
        `pp.funBinderTypes true) do
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

/-- The first ancestor, nearest first as given, whose statement the hole is (F07-T34). Asked of
the hole's type where it sits and of its closed form, as the goal check asks both, because an
ancestor's statement can arrive either way: written out whole under the node's binders (the type
where it sits), or reached by closing the hole over them (the closed form). The same two
transparencies; a comparison that throws is not a match. -/
private def restatesAncestor (ancestors : Array (String × Expr)) (t closed : Expr)
    : MetaM (Option String) := do
  for (node, ty) in ancestors do
    let same ← try
        withReducible (isDefEq t ty) <||> withReducible (isDefEq closed ty) <||>
          isDefEq t ty <||> isDefEq closed ty
      catch _ => pure false
    if same then return some node
  return none

/-- What each hole is compared with: the node's goal and statement, the target's other statements
(F07-T7) and the node's ancestors (F07-T34). -/
private structure Known where
  goal : Expr
  stmt : Expr
  siblings : Array (String × Expr)
  ancestors : Array (String × Expr)

/-- Does `e` rest on `sorry`, directly or through a constant this file defined (an auxiliary lemma
or matcher the elaborator made from the assembly)? Let-bound locals are unfolded first, so a
proved `have` whose own proof hides a hole counts as resting on it. -/
private partial def restsOnSorry (e : Expr) (seen : NameSet := {}) : MetaM Bool := do
  let e ← instantiateMVars (← zetaReduce e)
  if (e.find? fun s => s.isConstOf ``sorryAx).isSome then return true
  let env ← getEnv
  let mut seen := seen
  for c in e.getUsedConstants do
    if seen.contains c || (env.getModuleIdxFor? c).isSome then continue
    seen := seen.insert c
    let some ci := env.find? c | continue
    let some v := ci.value? (allowOpaque := true) | continue
    if ← restsOnSorry v seen then return true
  return false

/-- D-29 v3.22 (F07-T44): is `e` `I.casesOn … major (fun fields => …) …` for a structure-like `I`
(one constructor, no indices, not recursive)? Then every value of `major` has those fields, so a
binder of the minor premise is a fact the assembly proved from the binders before it — whatever
values a witness gives them. Answers the argument positions of the major and minor premises and
the number of fields. `obtain ⟨hp, hq⟩ := pq` and `obtain ⟨x, hx⟩ : ∃ x, P x := …` elaborate to
exactly this (read from Lean 4.33.1, `engineering/evidence/F07/task-44.txt`); a `cases` on a
type with two constructors does not, and its branch hypotheses stay obligations, because a
witness must still show the branch can be reached. -/
private def structCases? (e : Expr) : MetaM (Option (Nat × Nat × Nat)) := do
  let .const c _ := e.getAppFn | return none
  let env ← getEnv
  unless isCasesOnRecursor env c do return none
  let some (.inductInfo iv) := env.find? c.getPrefix | return none
  unless iv.ctors.length == 1 && iv.numIndices == 0 && !iv.isRec do return none
  let some (.ctorInfo cv) := env.find? iv.ctors.head! | return none
  let major := iv.numParams + 1
  unless e.getAppNumArgs > major + 1 do return none
  return some (major, major + 1, cv.numFields)

/-- The indices, into `closed`'s leading `∀` binders, of the in-scope binders marked proved. A
`let` in scope (a proved `have`) is not a `∀` binder of the closed type: `mkForallFVars` drops it
when the hole's type does not use it, which is why a proved `have` was never a hypothesis. When one
is used and so sits in the spine as a `let`, the positions no longer name `∀` binders and nothing
is marked: the hole keeps the full expected type rather than a guessed one. -/
private def provedIndices (binders : Array Expr) (marks : Array Bool) (closed : Expr)
    : MetaM (Array Nat) := do
  let mut idx : Array Nat := #[]
  let mut pos := 0
  for (x, m) in binders.zip marks do
    if (← x.fvarId!.getDecl).isLet (allowNondep := true) then continue
    if m then idx := idx.push pos
    pos := pos + 1
  if idx.isEmpty then return #[]
  let mut e := closed
  for _ in [0:pos] do
    match e with
    | .forallE _ _ b _ => e := b
    | _ => return #[]
  return idx

mutual

/-- `binders` are the locals in scope, and `marks` says of each whether the assembly proved it
(F07-T44): a field of a structure it destructured. The statement's own binders, holes, `intro`s
and case branches are not. -/
private partial def scan (k : Known)
    (binders : Array Expr) (marks : Array Bool) (e : Expr) (acc : Acc) : TermElabM Acc := do
  let e := e.consumeMData
  if isSorry e then
    return { acc with unnamed := acc.unnamed + 1 }
  match e with
  | .letE n t v b _ =>
    if isSorry v then
      let closed ← instantiateMVars (← mkForallFVars binders t)
      let printed ← ppRoundTrippable closed
      let proved ← provedIndices binders marks closed
      let expected ← expectedWitnessTypeNarrowed closed proved
      let expectedPrinted ← ppRoundTrippable expected
      let expectedOk ← reElaboratesTo expectedPrinted expected
      let hole : Hole := {
        name := n.toString,
        type := ← ppRoundTrippable t,
        closed_type := printed,
        defeq_goal := ← restatesGoal k.goal k.stmt t closed,
        defeq_sibling := ← restatesSibling k.siblings closed,
        defeq_ancestor := ← restatesAncestor k.ancestors t closed,
        closed_roundtrip := ← reElaboratesTo printed closed,
        expected_witness := if expectedOk then some expectedPrinted else none,
        proved_binders := proved }
      let acc := { acc with holes := acc.holes.push hole }
      withLocalDeclD n t fun x => scan k (binders.push x) (marks.push false) (b.instantiate1 x) acc
    else
      let acc ← scan k binders marks t acc
      let acc ← scan k binders marks v acc
      withLetDecl n t v fun x =>
        scan k (binders.push x) (marks.push false) (b.instantiate1 x) acc
  | .app .. =>
    match ← structCases? e with
    | some (major, minor, fields) =>
      let args := e.getAppArgs
      let proved := !(← restsOnSorry args[major]!)
      let mut acc := acc
      for i in [0:args.size] do
        acc ← if i == minor then scanFields k binders marks args[i]! fields proved acc
          else scan k binders marks args[i]! acc
      return acc
    | none =>
      let .app f a := e | return acc
      let acc ← scan k binders marks f acc
      scan k binders marks a acc
  | .lam n t b bi =>
    let acc ← scan k binders marks t acc
    withLocalDecl n bi t fun x => scan k (binders.push x) (marks.push false) (b.instantiate1 x) acc
  | .forallE n t b bi =>
    let acc ← scan k binders marks t acc
    withLocalDecl n bi t fun x => scan k (binders.push x) (marks.push false) (b.instantiate1 x) acc
  | .proj _ _ s => scan k binders marks s acc
  | _ => return acc

/-- The minor premise of a structure's `casesOn`: its first `left` binders are the fields, marked
`proved`; whatever follows (an equation a `rcases` threads through the motive, the body) is scanned
as anywhere else. A minor premise that is not a `fun` of that many binders is scanned unmarked. -/
private partial def scanFields (k : Known) (binders : Array Expr) (marks : Array Bool)
    (m : Expr) (left : Nat) (proved : Bool) (acc : Acc) : TermElabM Acc := do
  if left == 0 then return ← scan k binders marks m acc
  match m.consumeMData with
  | .lam n t b bi =>
    let acc ← scan k binders marks t acc
    withLocalDecl n bi t fun x =>
      scanFields k (binders.push x) (marks.push proved) (b.instantiate1 x) (left - 1) proved acc
  | other => scan k binders marks other acc

end

/-- Every hole in `value`, a proof of `stmt`; each named against `siblings`, the target's other
statements as `(node id, type)` (F07-T7), and against `ancestors`, the statements of the nodes that
depend on this one, nearest first (F07-T34); either is empty when the caller staged none. -/
def holeReport (stmt value : Expr) (siblings : Array (String × Expr) := #[])
    (ancestors : Array (String × Expr) := #[]) : TermElabM HoleReport := do
  lambdaTelescope value fun xs body => do
    let goal ← inferType body
    let acc ← scan { goal, stmt, siblings, ancestors } xs (xs.map fun _ => false) body {}
    return { holes := acc.holes, unnamed := acc.unnamed, body_is_hole := isSorry body }

end OpnGate
