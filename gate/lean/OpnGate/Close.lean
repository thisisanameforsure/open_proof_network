import Lean
import OpnGate.Frontend

/-!
The closing proof of a node whose merged decomposition has every hole proved (F28-R4, R6;
draft decisions v3.41).

**What it writes.** The merged assembly, unchanged except that each hole's value — the `sorry`
or `by sorry` after a `have`'s `:=` — is replaced by the hole node's theorem applied to the
locals in scope. Nothing else in the file moves, so the result is the statement with its `sorry`
replaced (step 2), its imports are the assembly's, and the children are the node's declared
dependencies whose signatures its own `Context.lean` already holds (step 4 imports their proofs
in their place).

**How the arguments are found (F28-Q6).** Not from the hole's name, which an assembly may repeat
(`hole-witness-ambiguous`), and not by re-deriving the extractor's binder list, which reads the
elaborated term rather than the tactic context. The child's statement as the gate wrote it is the
ground truth: each hole site's goal is unified with the conclusion of each child's statement, in
the route's order, and every binder the conclusion does not fix is filled from the locals in
scope, preferring the local whose name the binder carries (the extractor names binders after the
locals it closed over), backtracking on failure. Any choice that type-checks is a proof, so a
wrong choice can cost a failure, never a false proof.

**Names that cannot be written (ruling 1 of 2026-10-15).** A local that is inaccessible (`n✝`,
from an unnamed `intro` or a pattern) or shadowed by a later one of the same name has no source
spelling. Every such local in scope is named by a `rename_i` at the start of the replacement, in
context order, which on Lean 4.33.1 reaches shadowed locals too (probed 2026-10-15). The
replacement is then elaborated against the hole's own goal in its own context before it is
emitted, and the composed file is elaborated whole: the program never prints a replacement it
has not seen close its goal.

Elaborating the assembly runs its code: this program runs only in the step-3 sandbox (D-4), and
what it prints is a proposal the gate then judges like any proof (D-12 v3.41).
-/
open Lean Elab Meta

namespace OpnGate.Close

/-- One child the route offers: its node id and its theorem's name. -/
structure Child where
  node : String
  decl : Name

/-- One hole site, composed or not. -/
structure Site where
  start : String.Pos.Raw
  stop : String.Pos.Raw
  line : Nat
  child : Option String := none
  text : Option String := none
  problem : Option String := none
  /-- For a hole no child closed: each child tried and where it failed. -/
  tried : Array String := #[]

def Site.toJson (s : Site) : Json :=
  Json.mkObj [
    ("start", Json.num s.start.byteIdx), ("stop", Json.num s.stop.byteIdx),
    ("line", Json.num s.line),
    ("child", match s.child with | some c => Json.str c | none => Json.null),
    ("text", match s.text with | some t => Json.str t | none => Json.null),
    ("problem", match s.problem with | some p => Json.str p | none => Json.null),
    ("tried", Json.arr (s.tried.map Json.str))]

def kindIs (stx : Syntax) (k : Name) : Bool := stx.getKind == k

def rangeOf (stx : Syntax) : Option Syntax.Range := stx.getRange? (canonicalOnly := true)

/-- The value after `:=` of a `have`'s `letDecl` (the outline's reading, F19). -/
partial def letValue? (stx : Syntax) : Option Syntax :=
  if kindIs stx ``Lean.Parser.Term.letIdDecl || kindIs stx ``Lean.Parser.Term.letPatDecl then
    some stx.getArgs.back!
  else stx.getArgs.findSome? letValue?

/-- `sorry`, or `by sorry` written as a whole value. -/
partial def isHoleValue (v : Syntax) : Bool :=
  if kindIs v ``Lean.Parser.Term.sorry then true
  else if kindIs v ``Lean.Parser.Term.byTactic then onlySorry v[1]
  else false
where
  onlySorry (stx : Syntax) : Bool :=
    if kindIs stx ``Lean.Parser.Tactic.tacticSorry then true
    else if stx.isOfKind nullKind || kindIs stx ``Lean.Parser.Tactic.tacticSeq ||
        kindIs stx ``Lean.Parser.Tactic.tacticSeq1Indented ||
        kindIs stx ``Lean.Parser.Tactic.tacticSeqBracketed then
      let args := stx.getArgs.filter fun a => !(a.isAtom || (a.isOfKind nullKind && a.getNumArgs == 0))
      args.size == 1 && onlySorry args[0]!
    else false

def isHave (stx : Syntax) : Bool :=
  kindIs stx ``Lean.Parser.Tactic.tacticHave__ || kindIs stx ``Lean.Parser.Term.have

/-- Every hole value under `stx`, in source order. -/
partial def holeValues (stx : Syntax) : Array Syntax :=
  let here : Array Syntax :=
    if isHave stx then
      match letValue? stx with
      | some v => if isHoleValue v then #[v] else #[]
      | none => #[]
    else #[]
  stx.getArgs.foldl (fun acc a => acc ++ holeValues a) here

/-- The info the elaborator recorded for exactly this term syntax. -/
def termInfoFor (infos : Array (ContextInfo × Info)) (stx : Syntax) :
    Option (ContextInfo × TermInfo) := do
  let r ← rangeOf stx
  infos.findSome? fun (ci, info) => match info with
    | .ofTermInfo ti => if rangeOf ti.stx == some r then some (ci, ti) else none
    | _ => none

/-- The `sorry` tactic inside a `by sorry` value, if that is what the value is. -/
partial def sorryTactic? (stx : Syntax) : Option Syntax :=
  if kindIs stx ``Lean.Parser.Tactic.tacticSorry then some stx
  else stx.getArgs.findSome? sorryTactic?

/-- The tactic info the elaborator recorded for exactly this tactic syntax. -/
def tacticInfoFor (infos : Array (ContextInfo × Info)) (stx : Syntax) :
    Option (ContextInfo × TacticInfo) := do
  let r ← rangeOf stx
  infos.findSome? fun (ci, info) => match info with
    | .ofTacticInfo ti =>
      if ti.stx.getKind == stx.getKind && rangeOf ti.stx == some r then some (ci, ti) else none
    | _ => none

/-- Where a hole's goal and local context come from: the term the value elaborated as (a bare
`sorry`), or, for `by sorry`, the goal the `sorry` tactic closed — the elaborator records no term
info with the `by` block's exact range (found on the live erdos-1094 assembly, 2026-10-15). -/
def holeGoal (infos : Array (ContextInfo × Info)) (v : Syntax) :
    Option (ContextInfo × LocalContext × MetaM Expr) :=
  match termInfoFor infos v with
  | some (ci, ti) =>
    some (ci, ti.lctx, do
      match ti.expectedType? with
      | some t => instantiateMVars t
      | none => instantiateMVars (← inferType ti.expr))
  | none => do
    let tac ← sorryTactic? v
    let (ci, ti) ← tacticInfoFor infos tac
    let g ← ti.goalsBefore.head?
    let decl ← ti.mctxBefore.findDecl? g
    some ({ ci with mctx := ti.mctxBefore }, decl.lctx, instantiateMVars decl.type)

/-- A local that source text cannot name: inaccessible, or shadowed by a later local. -/
def unwritable (lctx : LocalContext) (d : LocalDecl) : Bool :=
  d.userName.hasMacroScopes || d.userName.isInaccessibleUserName ||
    (lctx.findFromUserName? d.userName).map (·.fvarId) != some d.fvarId

/-- The locals a replacement may use, in context order. -/
def usable (lctx : LocalContext) : Array LocalDecl :=
  lctx.foldl (fun acc d => if d.isImplementationDetail then acc else acc.push d) #[]

/-- A fresh name that no local in scope carries. -/
def freshNames (lctx : LocalContext) (n : Nat) : Array Name := Id.run do
  let mut out := #[]
  let mut i := 1
  while out.size < n do
    let cand := Name.mkSimple s!"opn_l{i}"
    if (lctx.findFromUserName? cand).isNone then out := out.push cand
    i := i + 1
  return out

/-- The free variables of `e`. -/
def fvarsIn (e : Expr) : Array FVarId :=
  (Lean.collectFVars {} e).fvarIds

/-- How deep a cleared premise is rebuilt from constructors (`⟨k, ⟨h1, h2⟩⟩` is two). -/
def constructDepth : Nat := 3

mutual

/-- Assign `m` from the locals (the one carrying `want` first, then the rest innermost first),
from instance synthesis, or, failing both, by rebuilding it from a constructor whose fields the
locals supply. The last is what a premise a tactic cleared needs: `obtain ⟨k, hk⟩ := h` removes
`h`, `rcases h with h | h` replaces it, and the extractor's child still takes it, since it reads
the elaborated term where `h` is a binder. Any value that type-checks will do, the kernel judging
the result. `k` continues the search, so a choice a later binder cannot live with is undone. -/
partial def supply (locals : Array LocalDecl) (m : Expr) (want : Name) (depth : Nat)
    (k : MetaM Bool) : MetaM Bool := do
  let named := locals.filter (·.userName.eraseMacroScopes == want.eraseMacroScopes)
  let rest := locals.reverse.filter (·.userName.eraseMacroScopes != want.eraseMacroScopes)
  for d in named ++ rest do
    let saved ← saveState
    if ← isDefEq m d.toExpr then
      if ← k then return true
    saved.restore
  let ty ← instantiateMVars (← inferType m)
  if let some inst ← (try synthInstance? ty catch _ => pure none) then
    let saved ← saveState
    if ← isDefEq m inst then
      if ← k then return true
    saved.restore
  if depth == 0 then return false
  let ty ← whnfR ty
  let .const indName _ := ty.getAppFn | return false
  let some (.inductInfo ind) := (← getEnv).find? indName | return false
  for ctor in ind.ctors do
    let saved ← saveState
    let c ← mkConstWithFreshMVarLevels ctor
    let (args, _, res) ← forallMetaTelescope (← inferType c)
    if ← isDefEq res ty then
      let fields := args.extract ind.numParams args.size
      let ok ← fillAll locals fields #[] 0 (depth - 1) do
        if ← isDefEq m (mkAppN c args) then k else pure false
      if ok then return true
    saved.restore
  return false

/-- Fill each unassigned metavariable of `mvars` in order (`names` the binder names they came
from), then run `k`; backtracking. -/
partial def fillAll (locals : Array LocalDecl) (mvars : Array Expr) (names : Array Name) (i : Nat)
    (depth : Nat) (k : MetaM Bool) : MetaM Bool := do
  if h : i < mvars.size then
    let m := mvars[i]
    if (← instantiateMVars m).isMVar then
      supply locals m (names[i]?.getD .anonymous) depth
        (fillAll locals mvars names (i + 1) depth k)
    else fillAll locals mvars names (i + 1) depth k
  else k

end

/-- Fill every binder the conclusion left open. -/
def fill (locals : Array LocalDecl) (mvars : Array Expr) (names : Array Name) : MetaM Bool :=
  fillAll locals mvars names 0 constructDepth (pure true)

/-- The child's binders as metavariables and its conclusion, through `let`s and nothing else.
Not `forallMetaTelescopeReducing`, which unfolds `a ≠ b` and `¬ p` into `… → False` and so takes
binders the statement does not have (case C14 of 2026-10-15).

A `let` in the child's spine is a proved `have` the hole's type used (`Holes.closedOver`): the
child knows its value, the tactic context does not, because `have` forgets it (case C9). Where a
local of the same name and type is in scope, the `let` is read as that local and returned with
its value, so the caller can make the local a `let` (the assembly's `have` written `let`) and the
child's conclusion is the hole's goal again. -/
partial def telescope (lctx : LocalContext) (e : Expr) (mvars : Array Expr := #[])
    (names : Array Name := #[]) (lets : Array (FVarId × Expr) := #[]) :
    MetaM (Array Expr × Array Name × Expr × Array (FVarId × Expr)) := do
  match e.consumeMData with
  | .forallE n t b bi =>
    let m ← mkFreshExprMVar (t.instantiateRev mvars)
      (if bi.isInstImplicit then .synthetic else .natural) n
    telescope lctx b (mvars.push m) (names.push n) lets
  | .letE n t v b _ =>
    let t' := t.instantiateRev mvars
    let v' := v.instantiateRev mvars
    match lctx.findFromUserName? n with
    | some d =>
      if !d.isImplementationDetail && (← isDefEq d.type t') then
        let lets := if d.isLet then lets else lets.push (d.fvarId, v')
        telescope lctx (b.instantiate1 d.toExpr) mvars names lets
      else telescope lctx (b.instantiate1 v') mvars names lets
    | none => telescope lctx (b.instantiate1 v') mvars names lets
  | body => return (mvars, names, body.instantiateRev mvars, lets)

/-- The argument text for one filled binder: a local's written name; a constructor rebuilt from
locals, every other argument `_`; and `_` for anything else, which unification fixes again when
the replacement is elaborated. -/
partial def argText (lctx : LocalContext) (renamed : Std.HashMap FVarId Name) (e : Expr) :
    MetaM String := do
  let e ← instantiateMVars e
  match e.consumeMData with
  | .fvar id =>
    match renamed.get? id with
    | some n => return n.toString
    | none => match lctx.find? id with
      | some d => return if unwritable lctx d then "_" else d.userName.toString
      | none => return "_"
  | e =>
    match e.getAppFn with
    | .const n _ =>
      if (← getEnv).isConstructor n && e.getAppArgs.any (·.consumeMData.isFVar) then
        let parts ← e.getAppArgs.mapM fun a => do
          if a.consumeMData.isFVar || a.consumeMData.getAppFn.isConst then argText lctx renamed a
          else pure "_"
        return s!"(@{(`_root_ ++ n).toString}" ++ String.join (parts.toList.map (" " ++ ·)) ++ ")"
      else return "_"
    | _ => return "_"

/-- Elaborate `text` as a term of type `goal` in the current context; whether it closes it with
nothing left open. -/
def closes (text : String) (goal : Expr) : TermElabM Bool := do
  let env ← getEnv
  let stx ← match Parser.runParserCategory env `term text with
    | .ok s => pure s
    | .error _ => return false
  let saved ← saveState
  try
    let v ← Term.elabTermEnsuringType stx goal
    Term.synthesizeSyntheticMVarsNoPostponing
    let v ← instantiateMVars v
    let ok := !v.hasMVar && !v.hasSorry && (← isDefEq (← inferType v) goal)
    saved.restore
    return ok
  catch _ =>
    saved.restore
    return false

/-- One composed site: the child it used, the replacement text, and the locals whose `have`
must be written `let` for the replacement to check (case C9). -/
structure Composed where
  node : String
  text : String
  lets : Array FVarId

/-- The replacement for one hole site, from the first child whose statement closes it; or, for
each child tried, the stage at which it failed. -/
def composeSite (lctx : LocalContext) (goal : Expr) (children : Array Child) :
    TermElabM (Except (Array String) Composed) := do
  let locals := usable lctx
  let hidden := locals.filter (unwritable lctx)
  let fresh := freshNames lctx hidden.size
  let mut renamed : Std.HashMap FVarId Name := {}
  for d in hidden, n in fresh do
    renamed := renamed.insert d.fvarId n
  let mut why : Array String := #[]
  for c in children do
    let saved ← saveState
    let some info := (← getEnv).find? c.decl
      | why := why.push s!"{c.node}: {c.decl} is not declared"; continue
    let (mvars, names, concl, lets) ← telescope lctx (← instantiateTypeLevelParams
      info.toConstantVal ((← mkConstWithFreshMVarLevels c.decl).constLevels!))
    if !(← isDefEq concl goal) then
      why := why.push s!"{c.node}: its conclusion is not the hole's goal"
      saved.restore
      continue
    if !(← fill locals mvars names) then
      let mut open_ : Array String := #[]
      for m in mvars, n in names do
        if (← instantiateMVars m).isMVar then
          open_ := open_.push
            s!"{n.eraseMacroScopes} : {← ppExpr (← instantiateMVars (← inferType m))}"
      why := why.push s!"{c.node}: nothing in scope fills {", ".intercalate open_.toList}"
      saved.restore
      continue
    let args ← mvars.mapM instantiateMVars
    let lets ← lets.mapM fun (id, v) => return (id, ← instantiateMVars v)
    let argStrs ← args.mapM fun a => (argText lctx renamed a : MetaM String)
    let call := s!"@{(`_root_ ++ c.decl).toString}" ++
      String.join (argStrs.toList.map (" " ++ ·))
    saved.restore
    let used := args.any fun a => (fvarsIn a).any renamed.contains
    let text :=
      if used then
        s!"(by rename_i {" ".intercalate (fresh.toList.map toString)}; exact {call})"
      else s!"({call})"
    -- Checked where it will live: with each `have` the child needs written `let`, its value.
    let lctx' := lets.foldl (init := lctx) fun l (id, v) =>
      l.modifyLocalDecl id fun d => .ldecl d.index d.fvarId d.userName d.type v false d.kind
    if ← withLCtx lctx' (← getLocalInstances) (closes text goal) then
      return .ok { node := c.node, text, lets := lets.map (·.1) }
    why := why.push s!"{c.node}: {text} does not close the hole"
  return .error why

/-- The `have` keyword that introduced local `id`, found through the binder the elaborator
recorded for it: its range, to be written `let` (case C9). -/
partial def haveKeywordFor (infos : Array (ContextInfo × Info)) (cmd : Syntax) (id : FVarId) :
    Option Syntax.Range := do
  let binder ← infos.findSome? fun (_, info) => match info with
    | .ofTermInfo ti =>
      if ti.isBinder && ti.expr.consumeMData == .fvar id then rangeOf ti.stx else none
    | _ => none
  find binder cmd
where
  find (binder : Syntax.Range) (stx : Syntax) : Option Syntax.Range :=
    let here : Option Syntax.Range :=
      if isHave stx && (identOf stx).bind rangeOf == some binder then rangeOf stx[0] else none
    here.orElse fun _ => stx.getArgs.findSome? (find binder)
  identOf (stx : Syntax) : Option Syntax :=
    if kindIs stx ``Lean.Parser.Term.letIdDecl then
      -- `letIdDecl` starts with a `letId` (or, in older shapes, the ident itself)
      let h := stx[0]
      if h.isIdent then some h else h.getArgs.find? (·.isIdent)
    else stx.getArgs.findSome? identOf

/-- Elaborate `path` as `module`, keeping the header environment and the info trees. -/
def elaborate (path : System.FilePath) (moduleName : Name) :
    IO (Environment × Environment × MessageLog × Array InfoTree × FileMap) := do
  let input ← IO.FS.readFile path
  let inputCtx := Parser.mkInputContext input path.toString
  let (stx, parserState, messages) ← Parser.parseHeader inputCtx
  let (env0, messages) ← processHeader stx {} messages inputCtx (mainModule := moduleName)
  let s ← IO.processCommands inputCtx parserState (Command.mkState env0 messages {})
  return (env0, s.commandState.env, s.commandState.messages,
    s.commandState.infoState.trees.toArray, inputCtx.fileMap)

/-- The info tree of the command that declared `decl`, and its infos. -/
def declInfos (trees : Array InfoTree) (decl : Name) :
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

/-- Replace each range by its text, in one pass over `input` (ranges in source order). -/
def splice (input : String) (edits : Array (String.Pos.Raw × String.Pos.Raw × String)) : String :=
  Id.run do
    let mut out := ""
    let mut at_ : String.Pos.Raw := 0
    for (a, b, t) in edits do
      out := out ++ String.Pos.Raw.extract input at_ a ++ t
      at_ := b
    return out ++ String.Pos.Raw.extract input at_ input.rawEndPos

/-- The whole run: the sites, the composed text, and whether that text elaborates whole with no
`sorry` left in `decl`. -/
def compose (path : System.FilePath) (moduleName decl : Name) (children : Array Child) :
    IO Json := do
  let input ← IO.FS.readFile path
  let (env0, _, log, trees, fileMap) ← elaborate path moduleName
  if log.hasErrors then
    let msgs ← messagesToArray log
    let errs := (msgs.filter (·.severity == "error")).map (·.text)
    throw <| IO.userError s!"assembly does not elaborate: {"; ".intercalate errs.toList}"
  let some (cmd, infos) := declInfos trees decl
    | throw <| IO.userError s!"no elaboration record of {decl}"
  let values := holeValues cmd
  if values.isEmpty then throw <| IO.userError s!"{decl} has no hole to close"
  let mut sites : Array Site := #[]
  let mut letEdits : Array (String.Pos.Raw × String.Pos.Raw × String) := #[]
  for v in values do
    let some r := rangeOf v | throw <| IO.userError "a hole has no source position"
    let base : Site := { start := r.start, stop := r.stop, line := (fileMap.toPosition r.start).line }
    match holeGoal infos v with
    | none => sites := sites.push { base with problem := some "no elaboration record of the hole" }
    | some (ci, lctx, goalM) =>
      let res ← ci.runMetaM lctx do
        let goal ← goalM
        (composeSite lctx goal children).run' {}
      match res with
      | .ok c =>
        sites := sites.push { base with child := some c.node, text := some c.text }
        for id in c.lets do
          match haveKeywordFor infos cmd id with
          | some kw => letEdits := letEdits.push (kw.start, kw.stop, "let")
          | none => sites := sites.modify (sites.size - 1) fun s =>
              { s with problem := some "a `have` the child needs as `let` was not found" }
      | .error why =>
        sites := sites.push { base with problem := some "no child's statement closes this hole",
                                        tried := why }
  let ok := sites.all (·.problem.isNone)
  if !ok then
    return Json.mkObj [("ok", Json.bool false), ("error", Json.str "a hole could not be closed"),
      ("sites", Json.arr (sites.map Site.toJson))]
  let edits := (sites.map fun s => (s.start, s.stop, s.text.getD "")) ++
    (letEdits.toList.eraseDups.toArray)
  let edits := edits.qsort fun a b => a.1.byteIdx < b.1.byteIdx
  let composed := splice input edits
  -- The composed file, elaborated whole on the same imports (imports happen once per process).
  let tmp := path.withExtension "closing.lean"
  IO.FS.writeFile tmp composed
  let (env2, log2) ← elabFile tmp moduleName (some env0)
  IO.FS.removeFile tmp
  let errs := ((← messagesToArray log2).filter (·.severity == "error")).map (·.text)
  let clean := match env2.find? decl with
    | some info => match info.value? (allowOpaque := true) with
      | some v => !v.hasSorry
      | none => false
    | none => false
  if !errs.isEmpty || !clean then
    return Json.mkObj [("ok", Json.bool false),
      ("error", Json.str s!"the composed proof does not check: {"; ".intercalate errs.toList}"),
      ("sites", Json.arr (sites.map Site.toJson)), ("composed", Json.str composed)]
  return Json.mkObj [("ok", Json.bool true), ("sites", Json.arr (sites.map Site.toJson)),
    ("composed", Json.str composed)]

end OpnGate.Close
