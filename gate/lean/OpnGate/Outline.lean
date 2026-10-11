import Lean
import OpnGate.Frontend
import OpnGate.Holes

/-!
The outline of one proof artifact (F19-R1 to R4): its named steps, each with the claim it
establishes, the goal it leaves, the constants it uses and how it is closed, read from the gate's
own frontend and the elaborator's info trees (F19-Q3: no SubVerso, no dependency).

**What a step is (F19-Q4).** Read from the artifact's *source syntax*, never from macro
expansions: every `have`, `obtain`, `suffices`, `show`, each step of a `calc`, and every case
branch (`case`, `next`, a `·` focus, an alternative of `cases`/`induction … with`), at any depth.
Every other tactic folds into the step that contains it. A step's children are the steps written
inside it. A proof that is not a `by` block is one `term` step. A `have` whose value is `sorry`
(or `by sorry`) is a `hole` step: a partial's named hole (D-12). The top-level tactics after a
`by` block's last step, which no step encloses, are one `term` step marked with the reserved id
`close` (F22-T14): its claim is the goal they close, and it takes no `s<n>` position, so no id
an outline already published moves.

**Goals and claims** come from the info tree: the `TacticInfo` the elaborator recorded for the
step's own syntax (same kind, same source range), its goals before and after. A goal carries its
target and the hypotheses the step introduced (locals of the goal after that the goal before did
not have), never the whole context; a case branch's, the locals it has that the goal before
its split had not (F22-T14). Each text is printed with the hole writer's options
(`ppRoundTrippable`) and read back in the goal's own local context (`reElaboratesTo`: parse,
elaborate, definitional equality); one that does not read back is `unreliable` (F19-R3).

**How a step is closed.** Its closing block is the value after `:=` (`have`, `obtain`, a `calc`
step), the branch's body, or, for `show` and `suffices`, the tactics after it in the same
sequence. `automation` when every tactic of the block (through `;`, `<;>`, `·` and parentheses)
leads with a name on the configured list (F19-Q5; passed as `--automation`, C6), `term` for a
term, `hole` for `sorry`, and `steps` otherwise.

**Constants** are the identifiers written in the source (original syntax only) that elaborated to
a constant, each given to the innermost step whose source contains it. Each is reported with its
module; for a module under one of the `--doc-modules` prefixes, with its docstring
(`findDocString?`) and any Stacks or Kerodon tag Mathlib's cross-reference attribute records. The
tags are read by evaluating `Lean.Environment.getSortedCrossRefs` (Mathlib's
`Mathlib.Tactic.CrossRefAttribute`) when the environment has it; Lean core has no such attribute
and then every constant's tags are empty. Which constants are graph nodes, definitions or
library is decided on the Python side from the module (`layout.module_origin`), the gate's one
reading of a module name.

Elaborating the artifact runs its code: this program runs only in the step-3 sandbox (D-4).
-/
open Lean Elab Meta

namespace OpnGate.Outline

/-- A printed claim, goal target or hypothesis type, and whether it read back (F19-R3). -/
structure PText where
  text : String
  reliable : Bool

instance : ToJson PText where
  toJson p := Json.mkObj [("text", Json.str p.text),
    ("printed", Json.str (if p.reliable then "reliable" else "unreliable"))]

structure Hyp where
  name : String
  type : PText

instance : ToJson Hyp where
  toJson h := Json.mkObj [("name", Json.str h.name), ("type", toJson h.type)]

structure GoalOut where
  target : PText
  hypotheses : Array Hyp

instance : ToJson GoalOut where
  toJson g := Json.mkObj [("target", toJson g.target), ("hypotheses", toJson g.hypotheses)]

structure StepOut where
  kind : String
  name : Option String := none
  claim : Option PText := none
  goal : Option GoalOut := none
  startPos : String.Pos.Raw
  stopPos : String.Pos.Raw
  startLine : Nat
  endLine : Nat
  uses : Array Name := #[]
  closedKind : String
  tactics : Array String := #[]
  children : Array StepOut := #[]
  /-- An id the step is given outright rather than by position (F22-T14: `close`). -/
  reserved : Option String := none
deriving Inhabited

partial def StepOut.toJson (s : StepOut) : Json :=
  Json.mkObj <| (match s.reserved with | some r => [("id", Json.str r)] | none => []) ++ [
    ("kind", Json.str s.kind),
    ("name", match s.name with | some n => Json.str n | none => Json.null),
    ("claim", match s.claim with | some c => ToJson.toJson c | none => Json.null),
    ("goal", match s.goal with | some g => ToJson.toJson g | none => Json.null),
    ("span", Json.mkObj [("start_line", Json.num s.startLine), ("end_line", Json.num s.endLine)]),
    ("uses", ToJson.toJson (s.uses.map toString)),
    ("closed_by", Json.mkObj [("kind", Json.str s.closedKind),
      ("tactics", ToJson.toJson s.tactics)]),
    ("children", Json.arr (s.children.map StepOut.toJson))]

/-- What the walk needs: the source, the info recorded under the declaration, the options. -/
structure Env where
  fileMap : FileMap
  infos : Array (ContextInfo × Info)
  automation : Array String
  /-- `false` only for the lean tier's stubbed printer (F19-AC3): default `ppExpr`, which drops
  coercion ascriptions, so a claim over the integers with natural casts does not read back. -/
  roundTrip : Bool := true

/-! ### Syntax helpers -/

def kindIs (stx : Syntax) (k : Name) : Bool := stx.getKind == k

/-- The canonical (written) source range of `stx`, if it has one. -/
def rangeOf (stx : Syntax) : Option Syntax.Range := stx.getRange? (canonicalOnly := true)

def within (inner outer : Syntax.Range) : Bool :=
  outer.start ≤ inner.start && inner.stop ≤ outer.stop

/-- The first atom of `stx`, which names the tactic it is (`simp only [..]` is `simp`). -/
partial def leadingAtom (stx : Syntax) : Option String :=
  match stx with
  | .atom _ v => some v
  | .node _ _ args => args.findSome? leadingAtom
  | _ => none

/-- Node kinds that only sequence or group tactics: their tactics are the block's tactics. -/
def isGrouping (stx : Syntax) : Bool :=
  stx.isOfKind nullKind || kindIs stx ``Lean.Parser.Tactic.tacticSeq ||
  kindIs stx ``Lean.Parser.Tactic.tacticSeq1Indented ||
  kindIs stx ``Lean.Parser.Tactic.tacticSeqBracketed ||
  kindIs stx ``Lean.Parser.Tactic.paren || kindIs stx ``Lean.cdot ||
  kindIs stx ``Lean.Parser.Term.byTactic || kindIs stx ``Lean.Parser.Tactic.«tactic_<;>_»

/-- The tactics of a closing block, in source order: the leading name of each tactic, looking
through the grouping forms. Separators (`;`, `<;>`, `by`, `·`, brackets) are not tactics. -/
partial def blockTactics (stx : Syntax) : Array String :=
  match stx with
  | .atom .. | .ident .. | .missing => #[]
  | .node _ _ args =>
    if isGrouping stx then args.foldl (fun acc a => acc ++ blockTactics a) #[]
    else match leadingAtom stx with
      | some v => #[v]
      | none => #[]

def dedup (xs : Array String) : Array String :=
  xs.foldl (fun acc x => if acc.contains x then acc else acc.push x) #[]

/-- How a block closes its step (F19-Q5). `sorry` alone is a hole. -/
def closing (env : Env) (block : Array Syntax) : String × Array String :=
  match block with
  | #[b] =>
    if kindIs b ``Lean.Parser.Term.sorry then ("hole", #[])
    else if !(kindIs b ``Lean.Parser.Term.byTactic) && !(b.getKind.toString.startsWith
        "Lean.Parser.Tactic") && !isGrouping b then ("term", #[])
    else classify (blockTactics b)
  | _ => classify (block.foldl (fun acc b => acc ++ blockTactics b) #[])
where
  classify (names : Array String) : String × Array String :=
    if names == #["sorry"] then ("hole", #[])
    else if !names.isEmpty && names.all env.automation.contains then
      ("automation", dedup names)
    else ("steps", #[])

/-! ### Info lookups -/

/-- The info the elaborator recorded for this very syntax: same kind, same written range. -/
def tacticInfoFor (env : Env) (stx : Syntax) : Option (ContextInfo × TacticInfo) := do
  let r ← rangeOf stx
  env.infos.findSome? fun (ci, info) => match info with
    | .ofTacticInfo ti =>
      if ti.stx.getKind == stx.getKind && rangeOf ti.stx == some r then some (ci, ti) else none
    | _ => none

def termInfoFor (env : Env) (stx : Syntax) : Option (ContextInfo × TermInfo) := do
  let r ← rangeOf stx
  env.infos.findSome? fun (ci, info) => match info with
    | .ofTermInfo ti => if rangeOf ti.stx == some r then some (ci, ti) else none
    | _ => none

/-- Print `e` and read it back where it lives (F19-R3). -/
def render (env : Env) (e : Expr) : MetaM PText := do
  let e ← instantiateMVars e
  let text ← if env.roundTrip then ppRoundTrippable e else toString <$> ppExpr e
  let ok ← (reElaboratesTo text e).run'
  return { text, reliable := ok }

def localName (d : LocalDecl) : String :=
  let base := d.userName.eraseMacroScopes.toString
  if d.userName.hasMacroScopes then base ++ "✝" else base

/-- The goal `after` leaves, with the hypotheses it has that `before`'s context had not. With no
`before` known, no hypothesis is reported: never the whole context (F19-Q4). -/
def goalOut (env : Env) (ci : ContextInfo) (mctx : MetavarContext) (after : MVarId)
    (before : Option LocalContext) : IO GoalOut :=
  { ci with mctx }.runMetaM {} do
    after.withContext do
      let decl ← after.getDecl
      let target ← render env decl.type
      let mut hyps : Array Hyp := #[]
      if let some b := before then
        for d in decl.lctx do
          if d.isImplementationDetail || b.contains d.fvarId then continue
          hyps := hyps.push { name := localName d, type := ← render env d.type }
      return { target, hypotheses := hyps }

/-- The lctx of a goal, read from a metavariable context. -/
def lctxOf (mctx : MetavarContext) (g : MVarId) : Option LocalContext :=
  (mctx.findDecl? g).map (·.lctx)

/-- The context of the goal before the split a branch's goal `g` came from (F22-T14): the
innermost written tactic that has `g` among its goals after and not before (a `rcases`, a
`constructor`, a `refine`), read in that tactic's own metavariable context. A goal another was
renamed into (`case inl a =>` assigns the goal it names to a fresh one carrying the new names)
is followed back to that goal first, at most `fuel` links; the renamed variable keeps its
`FVarId`, which is why the goal the branch starts on can never show it. `none` when no tactic
made `g`: an alternative of `cases … with` introduces its variables inside the tactic, and the
caller then reads against the goal before the enclosing tactic. -/
partial def splitBase (env : Env) (mctx : MetavarContext) (g : MVarId) (fuel : Nat := 4) :
    Option LocalContext := Id.run do
  let mut best : Option (Syntax.Range × TacticInfo) := none
  for (_, info) in env.infos do
    if let .ofTacticInfo ti := info then
      if ti.goalsAfter.contains g && !ti.goalsBefore.contains g then
        if let some r := rangeOf ti.stx then
          match best with
          | some (br, _) => if within r br then best := some (r, ti)
          | none => best := some (r, ti)
  if let some (_, ti) := best then
    return ti.goalsBefore.head?.bind (lctxOf ti.mctxBefore)
  if fuel == 0 then return none
  for (_, info) in env.infos do
    if let .ofTacticInfo ti := info then
      for g0 in ti.goalsBefore do
        if g0 != g then
          if let some e := mctx.getExprAssignmentCore? g0 then
            if e.consumeMData == .mvar g then
              return splitBase env mctx g0 (fuel - 1)
  return none

/-- The type of the local `after` has that `before` had not, the last such: what a `have`
binds. With its name. -/
def newLocal (env : Env) (ci : ContextInfo) (ti : TacticInfo) :
    IO (Option (String × PText)) := do
  let some after := ti.goalsAfter.head? | return none
  let some before := ti.goalsBefore.head? | return none
  let some bctx := lctxOf ti.mctxBefore before | return none
  { ci with mctx := ti.mctxAfter }.runMetaM {} do
    after.withContext do
      let mut found : Option LocalDecl := none
      for d in (← after.getDecl).lctx do
        if !d.isImplementationDetail && !bctx.contains d.fvarId then found := some d
      match found with
      | none => return none
      | some d => return some (localName d, ← render env d.type)

/-- The goal a tactic leaves (its first goal after), hypotheses relative to its first goal
before; `none` when it leaves no goal. -/
def leftBy (env : Env) (ci : ContextInfo) (ti : TacticInfo) : IO (Option GoalOut) := do
  let some after := ti.goalsAfter.head? | return none
  let before := ti.goalsBefore.head?.bind (lctxOf ti.mctxBefore)
  return some (← goalOut env ci ti.mctxAfter after before)

/-- The type a term's syntax elaborated to: the term itself when it is a type (`asType`). -/
def typeOfTerm (env : Env) (stx : Syntax) (asType : Bool) : IO (Option PText) := do
  let some (ci, ti) := termInfoFor env stx | return none
  ci.runMetaM ti.lctx do
    let e ← if asType then pure ti.expr else inferType ti.expr
    return some (← render env e)

/-- The type a term's syntax was elaborated against, when the elaborator recorded one. -/
def expectedOf (env : Env) (stx : Syntax) : IO (Option PText) := do
  let some (ci, ti) := termInfoFor env stx | return none
  let some ty := ti.expectedType? | return none
  ci.runMetaM ti.lctx do
    return some (← render env ty)

/-! ### The walk -/

def lineOf (env : Env) (p : String.Pos.Raw) : Nat := (env.fileMap.toPosition p).line

def stepKind? (stx : Syntax) : Option String :=
  if kindIs stx ``Lean.Parser.Tactic.tacticHave__ then some "have"
  else if kindIs stx ``Lean.Parser.Tactic.obtain then some "obtain"
  else if kindIs stx ``Lean.Parser.Tactic.tacticSuffices_ then some "suffices"
  else if kindIs stx ``Lean.Parser.Tactic.show then some "show"
  else if kindIs stx ``Lean.calcFirstStep || kindIs stx ``Lean.calcStep then some "calc"
  else if kindIs stx ``Lean.Parser.Tactic.case || kindIs stx ``Lean.cdot ||
      kindIs stx ``Lean.Parser.Tactic.«tacticNext_=>_» ||
      kindIs stx ``Lean.Parser.Tactic.inductionAlt then some "case"
  else none

/-- The value after `:=` of a `have`'s `letDecl`. -/
partial def letValue? (stx : Syntax) : Option Syntax :=
  if kindIs stx ``Lean.Parser.Term.letIdDecl || kindIs stx ``Lean.Parser.Term.letPatDecl then
    some stx.getArgs.back!
  else stx.getArgs.findSome? letValue?

/-- The body of a branch: its last argument that holds tactics. -/
def branchBody (stx : Syntax) : Syntax :=
  if kindIs stx ``Lean.Parser.Tactic.inductionAlt then stx[1] else stx.getArgs.back!

mutual

/-- The steps written under `stx`, in source order. `rest` is what follows `stx` in its
sequence, which closes a `show` or a `suffices`; `outer` the goal before the tactic that
encloses `stx`, for a branch without info of its own. -/
partial def walk (env : Env) (stx : Syntax) (rest : Array Syntax)
    (outer : Option LocalContext) : IO (Array StepOut) := do
  match stepKind? stx with
  | some kind => return #[← mkStep env kind stx rest outer]
  | none =>
    let outer := match tacticInfoFor env stx with
      | some (_, ti) => (ti.goalsBefore.head?.bind (lctxOf ti.mctxBefore)).orElse fun _ => outer
      | none => outer
    let args := stx.getArgs
    let mut out := #[]
    for i in [0:args.size] do
      out := out ++ (← walk env args[i]! (args.extract (i + 1) args.size) outer)
    return out

partial def mkStep (env : Env) (kind : String) (stx : Syntax) (rest : Array Syntax)
    (outer : Option LocalContext) : IO StepOut := do
  let some r := rangeOf stx | throw <| IO.userError s!"a {kind} step has no source position"
  let info := tacticInfoFor env stx
  let base : StepOut := {
    kind, startPos := r.start, stopPos := r.stop, startLine := lineOf env r.start,
    endLine := lineOf env r.stop, closedKind := "steps" }
  let here := match info with
    | some (_, ti) => (ti.goalsBefore.head?.bind (lctxOf ti.mctxBefore)).orElse fun _ => outer
    | none => outer
  let children ← walkArgs env stx here
  match kind with
  | "have" =>
    let value := (letValue? stx).getD Syntax.missing
    let (ck, tactics) := closing env #[value]
    let kind := if ck == "hole" then "hole" else "have"
    let (name, claim, goal) ← match info with
      | some (ci, ti) => do
        let bound ← newLocal env ci ti
        pure (bound.map (·.1), bound.map (·.2), ← leftBy env ci ti)
      | none => pure (none, none, none)
    return { base with kind, name, claim, goal, closedKind := ck, tactics, children }
  | "obtain" =>
    -- `obtain pat (: T)? (:= v)?`: the claim is `T` when written, else the type of `v`.
    let typeStx := if stx[2].getNumArgs ≥ 2 then some stx[2][1] else none
    let valueStx := if stx[3].getNumArgs ≥ 2 then some stx[3][1][0] else none
    let claim ← match typeStx, valueStx with
      | some t, _ => typeOfTerm env t true
      | none, some v => typeOfTerm env v false
      | none, none => pure none
    let (ck, tactics) := match valueStx with
      | some v => closing env #[v]
      | none => closing env rest
    let goal ← match info with
      | some (ci, ti) => leftBy env ci ti
      | none => pure none
    return { base with claim, goal, closedKind := ck, tactics, children }
  | "suffices" | "show" =>
    let (ck, tactics) := closing env rest
    let (claim, goal) ← match info with
      | some (ci, ti) => do
        let g ← leftBy env ci ti
        pure (g.map (·.target), g)
      | none => pure (none, none)
    let name ← if kind == "suffices" then
        pure ((stx[1][0].getArgs.find? (·.isIdent)).map (·.getId.eraseMacroScopes.toString))
      else pure none
    return { base with name, claim, goal, closedKind := ck, tactics, children }
  | "calc" =>
    -- `term (:= proof)?`: the claim is the relation the step states.
    let proof := if kindIs stx ``Lean.calcStep then some stx[2]
      else if stx[1].getNumArgs ≥ 2 then some stx[1][1] else none
    -- A later step's `_ = b` is elaborated from rewritten syntax, so its own term has no info at
    -- its written range; then the relation is what its proof was elaborated against.
    let claim ← match ← typeOfTerm env stx[0] true, proof with
      | some c, _ => pure (some c)
      | none, some p => expectedOf env p
      | none, none => pure none
    let (ck, tactics) := match proof with
      | some p => closing env #[p]
      | none => ("term", #[])
    return { base with claim, closedKind := ck, tactics, children }
  | _ =>
    -- A case branch binds nothing; its goal is the one its body starts on, with the hypotheses
    -- the split gave it: read against the goal before the split (F22-T14), never against `here`,
    -- the goal the branch starts on, which already holds them.
    let body := branchBody stx
    let (ck, tactics) := closing env #[body]
    let bodySeq := (body.getArgs.find? (fun a => kindIs a ``Lean.Parser.Tactic.tacticSeq)).getD body
    let goal ← match tacticInfoFor env bodySeq with
      | some (ci, ti) => match ti.goalsBefore.head? with
        | some g =>
          let base := (splitBase env ti.mctxBefore g).orElse fun _ => outer
          pure (some (← goalOut env ci ti.mctxBefore g base))
        | none => pure none
      | none => pure none
    return { base with goal, closedKind := ck, tactics, children }

partial def walkArgs (env : Env) (stx : Syntax) (outer : Option LocalContext) :
    IO (Array StepOut) := do
  let args := stx.getArgs
  let mut out := #[]
  for i in [0:args.size] do
    out := out ++ (← walk env args[i]! (args.extract (i + 1) args.size) outer)
  return out

end

/-! ### The closing step (F22-T14) -/

/-- The id the trailing closing tactics are given, outside the `s<n>` numbering. -/
def closeId : String := "close"

/-- A `by` block's top-level tactics, in source order. -/
def topTactics (proof : Syntax) : Array Syntax :=
  let inner := proof[1][0]
  if kindIs inner ``Lean.Parser.Tactic.tacticSeq1Indented then inner[0].getSepArgs
  else if kindIs inner ``Lean.Parser.Tactic.tacticSeqBracketed then inner[1].getSepArgs
  else #[]

/-- The tactics after the proof's last step, which no step encloses: one `close` step, its claim
the goal they close and its closing what they are. `none` when the last step ends the proof. -/
def closeStep (env : Env) (proof : Syntax) (steps : Array StepOut) :
    IO (Option StepOut) := do
  let last := steps.foldl (fun acc s => if acc < s.stopPos then s.stopPos else acc) ⟨0⟩
  let trailing := (topTactics proof).filter fun t => match rangeOf t with
    | some r => last ≤ r.start
    | none => false
  let some first := trailing[0]? | return none
  let some r0 := rangeOf first | return none
  let some r1 := rangeOf trailing.back! | return none
  let (ck, tactics) := closing env trailing
  let claim ← match tacticInfoFor env first with
    | some (ci, ti) => match ti.goalsBefore.head? with
      | some g =>
        let before : ContextInfo := { ci with mctx := ti.mctxBefore }
        before.runMetaM {} do
          g.withContext do return some (← render env (← g.getDecl).type)
      | none => pure none
    | none => pure none
  return some { kind := "term", reserved := some closeId, claim, startPos := r0.start,
                stopPos := r1.stop, startLine := lineOf env r0.start,
                endLine := lineOf env r1.stop, closedKind := ck, tactics }

/-- Give each written constant to the innermost step whose source contains it. -/
partial def assignUses (steps : Array StepOut) (consts : Array (String.Pos.Raw × Name)) :
    Array StepOut :=
  steps.map fun s =>
    let mine := consts.filter fun (p, _) => s.startPos ≤ p && p < s.stopPos
    let children := assignUses s.children mine
    let inChild (p : String.Pos.Raw) := s.children.any fun c => c.startPos ≤ p && p < c.stopPos
    let own := mine.filter (fun (p, _) => !inChild p) |>.map (·.2)
    let uses := own.foldl (fun acc n => if acc.contains n then acc else acc.push n) #[]
    { s with children, uses }

/-- Every identifier written inside `r` that elaborated to a constant, in source order. -/
def writtenConstants (infos : Array (ContextInfo × Info)) (r : Syntax.Range) :
    Array (String.Pos.Raw × Name) :=
  let found := infos.filterMap fun (_, info) => match info with
    | .ofTermInfo ti =>
      if ti.isBinder || !ti.stx.isIdent then none
      else match ti.expr.consumeMData, rangeOf ti.stx with
        | .const n _, some sr => if within sr r then some (sr.start, n) else none
        | _, _ => none
    | _ => none
  found.qsort (fun a b => a.1 < b.1)

/-! ### Docstrings and tags (F19-R4) -/

/-- The first sentence is cut on the Python side, where the cap is config; here the docstring. -/
def docOf (env : Environment) (n : Name) : IO (Option String) := do
  try findDocString? env n catch _ => pure none

/-- Mathlib's Stacks and Kerodon tags, by declaration, or empty when the environment has no
cross-reference attribute (Lean core). Read by evaluating Mathlib's own reader, so nothing here
depends on the extension's internal shape; a failure to read an attribute that exists is an
error, never an empty answer (C7). -/
unsafe def crossRefs (env : Environment) : IO (Std.HashMap Name (Array (String × String))) := do
  unless env.contains `Lean.Environment.getSortedCrossRefs do return {}
  let src := "fun (env : Lean.Environment) => (Lean.Environment.getSortedCrossRefs env).filterMap \
    fun t => if t.database matches .stacks then some (t.declName, \"stacks\", t.tag) \
    else if t.database matches .kerodon then some (t.declName, \"kerodon\", t.tag) else none"
  let tySrc := "Lean.Environment → Array (Lean.Name × String × String)"
  let ctx : Core.Context := { fileName := "<opn-outline>", fileMap := default }
  let (reader, _) ← (do
      let tyStx ← ofExcept (Parser.runParserCategory (← getEnv) `term tySrc)
      let ty ← Term.elabType tyStx
      let stx ← ofExcept (Parser.runParserCategory (← getEnv) `term src)
      Term.evalTerm (Environment → Array (Name × String × String)) ty stx
      : TermElabM (Environment → Array (Name × String × String))).run'.run'.toIO ctx { env }
  let mut out : Std.HashMap Name (Array (String × String)) := {}
  for (n, db, tag) in reader env do
    out := out.insert n ((out.getD n #[]).push (db, tag))
  return out

/-! ### Entry point -/

/-- Elaborate `path` as `module`, keeping the info trees: one per command. -/
def elaborate (path : System.FilePath) (moduleName : Name) :
    IO (Environment × MessageLog × Array InfoTree × FileMap) := do
  let input ← IO.FS.readFile path
  let inputCtx := Parser.mkInputContext input path.toString
  let (stx, parserState, messages) ← Parser.parseHeader inputCtx
  let (env, messages) ← processHeader stx {} messages inputCtx (mainModule := moduleName)
  let s ← IO.processCommands inputCtx parserState (Command.mkState env messages {})
  return (s.commandState.env, s.commandState.messages, s.commandState.infoState.trees.toArray,
    inputCtx.fileMap)

/-- The info tree of the command that declared `decl`, its command syntax, and its infos. -/
def declTree (trees : Array InfoTree) (decl : Name) :
    Option (Syntax × Array (ContextInfo × Info)) :=
  trees.findSome? fun t =>
    let infos := t.foldInfo (fun ci info acc => acc.push (ci, info)) #[]
    let declares := infos.any fun (_, info) => match info with
      | .ofTermInfo ti => ti.isBinder && ti.expr.consumeMData.isConstOf decl
      | _ => false
    if !declares then none
    else
      let cmd := infos.findSome? fun (_, info) => match info with
        | .ofCommandInfo c => if c.stx.getKind == ``Lean.Parser.Command.declaration then
            some c.stx else none
        | _ => none
      cmd.map (·, infos)

/-- The proof term of a declaration's command: what follows `:=`. -/
partial def proofOf (cmd : Syntax) : Option Syntax :=
  if kindIs cmd ``Lean.Parser.Command.declValSimple then some cmd[1]
  else cmd.getArgs.findSome? proofOf

/-- The whole outline, as the JSON document `opn-outline` prints. -/
unsafe def outline (path : String) (moduleName declName : Name) (automation : Array String)
    (docPrefixes : Array Name) (roundTrip : Bool) : IO (Except String Json) := do
  let (finalEnv, log, trees, fileMap) ← elaborate path moduleName
  if log.hasErrors then
    let msgs ← messagesToArray log
    return .error s!"artifact does not elaborate: {(msgs.filter (·.severity == "error")).map (·.text) |>.toList |> String.intercalate "; "}"
  let some info := finalEnv.find? declName | return .error s!"{declName} is not declared in {path}"
  let some (cmd, infos) := declTree trees declName
    | return .error s!"no elaboration record of {declName}"
  let some proof := proofOf cmd | return .error s!"{declName} has no `:=` proof"
  let some proofRange := rangeOf proof | return .error "the proof has no source position"
  let env : Env := { fileMap, infos, automation, roundTrip }
  let steps ← if kindIs proof ``Lean.Parser.Term.byTactic then do
      let steps ← walk env proof #[] none
      pure (steps ++ (← closeStep env proof steps).toArray)
    else do
      -- F19-AC6: a term-mode proof is one step, the statement its claim.
      let some (ci, _) := infos[0]? | return .error "no elaboration record of the command"
      let claim ← ci.runMetaM {} (render env info.type)
      pure #[{ kind := "term", claim, startPos := proofRange.start, stopPos := proofRange.stop,
               startLine := lineOf env proofRange.start, endLine := lineOf env proofRange.stop,
               closedKind := "term" : StepOut }]
  let consts := writtenConstants infos proofRange
  let steps := assignUses steps consts
  -- The constants table: module, and for a library module its docstring and tags.
  let tags ← crossRefs finalEnv
  let mut table : Array (String × Json) := #[]
  let mut seen : NameSet := {}
  for (_, n) in consts do
    if seen.contains n then continue
    seen := seen.insert n
    let module? := (finalEnv.getModuleIdxFor? n).map fun i => finalEnv.header.moduleNames[i.toNat]!
    let library := match module? with
      | some m => docPrefixes.contains m.getRoot
      | none => false
    let doc ← if library then docOf finalEnv n else pure none
    let ts := if library then tags.getD n #[] else #[]
    table := table.push (n.toString, Json.mkObj [
      ("module", match module? with | some m => Json.str m.toString | none => Json.null),
      ("doc", match doc with | some d => Json.str d | none => Json.null),
      ("tags", Json.arr (ts.map fun (db, t) =>
        Json.mkObj [("database", Json.str db), ("tag", Json.str t)]))])
  return .ok <| Json.mkObj [
    ("ok", Json.bool true),
    ("decl", Json.str declName.toString),
    ("steps", Json.arr (steps.map StepOut.toJson)),
    ("constants", Json.mkObj table.toList)]

end OpnGate.Outline
