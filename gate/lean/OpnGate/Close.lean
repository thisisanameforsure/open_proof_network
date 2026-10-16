import Lean
import OpnGate.Frontend
import OpnGate.Holes
import OpnGate.Compiled

/-!
The join (F28-T7; decisions v3.42): a node whose merged decomposition has every hole proved is
proved by construction, and this program makes that a kernel-checked declaration.

**What it does.** It elaborates the node's merged assembly as the node's own `Proof` module, so its
imports are the statement's and its children's merged (or joined) proofs are in scope. It takes
the assembly's elaborated term and replaces each hole — the value of a `have h : T := sorry` — by
the hole node's theorem applied to locals in scope, then adds the node's theorem with that term
through the kernel in an environment of the statement's imports, and writes the result as a
compiled module (`--out-olean`). Nothing is printed as source and nothing is parsed back: the
names, binders and tactic rewrites that made source composition fragile (F28-Q6, Q7, Q10) do not
arise, because at the level of terms every local of the hole's scope is present, cleared premises
and `have` values included.

**How the arguments are found.** The child's statement as the gate wrote it is the ground truth.
Its leading binders are opened one at a time, and at each depth its remaining body is compared
with the hole's type; the first depth at which they unify is the split between the locals the hole
was closed over and the hole's own statement (a hole may itself begin with `∀`). The binders the
comparison leaves open are filled from the locals in scope, the one carrying the binder's name
first, with backtracking. Any filling the kernel accepts is a proof; a wrong one only fails.

**What it guarantees.** The written module declares the node's theorem with its statement's type,
accepted by the kernel, using only the standard axioms (reported, `sorryAx` refused). A child that
does not state its gap — a revision weaker than the hole, a mis-written statement — makes the join
fail, never succeed: this is the guard the derived status rests on (v3.42).

Elaborating the assembly runs its code: this program runs only in the step-3 sandbox (D-4).
-/
open Lean Elab Meta

namespace OpnGate.Close

/-- One child the route offers: its node id and its theorem's name. -/
structure Child where
  node : String
  decl : Name

/-- The locals a filling may use, in context order. -/
def usable (lctx : LocalContext) : Array LocalDecl :=
  lctx.foldl (fun acc d => if d.isImplementationDetail then acc else acc.push d) #[]

/-- How deep a premise is rebuilt from constructors when nothing in scope has its type. -/
def constructDepth : Nat := 3

mutual

/-- Assign `m` from the locals (the one carrying `want` first, then the rest innermost first),
from instance synthesis, or by a constructor whose fields the locals supply; then run `k`,
undoing a choice `k` cannot live with. -/
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

/-- Fill each unassigned metavariable of `mvars` in order, then run `k`; backtracking. -/
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

/-- The child's binders as metavariables, with the body after each prefix: `(k, body)` for every
`k` from 0 to the number of leading binders. A `let` in the spine (a proved `have` the hole's type
used) is read as the same-named local in scope when there is one, else as its value. -/
partial def stages (lctx : LocalContext) (e : Expr) (mvars : Array Expr := #[])
    (names : Array Name := #[]) (acc : Array (Nat × Expr) := #[]) :
    MetaM (Array Expr × Array Name × Array (Nat × Expr)) := do
  let e := e.consumeMData
  let acc := acc.push (mvars.size, e.instantiateRev mvars)
  match e with
  | .forallE n t b bi =>
    let m ← mkFreshExprMVar (t.instantiateRev mvars)
      (if bi.isInstImplicit then .synthetic else .natural) n
    stages lctx b (mvars.push m) (names.push n) acc
  | .letE n t v b _ =>
    let t' := t.instantiateRev mvars
    let v' := v.instantiateRev mvars
    let x ← match lctx.findFromUserName? n with
      | some d => if !d.isImplementationDetail && (← isDefEq d.type t') then pure d.toExpr else pure v'
      | none => pure v'
    -- the let is not a binder: drop the stage recorded for it and continue in its body
    stages lctx (b.instantiate1 x) mvars names acc.pop
  | _ => return (mvars, names, acc)

/-- The term that proves a hole of type `goal` in the current context from the first child whose
statement it is, with that child's node; or, for each child, why not. -/
def fillHole (goal : Expr) (children : Array Child) :
    MetaM (Except (Array String) (String × Expr)) := do
  let lctx ← getLCtx
  let locals := usable lctx
  let mut why : Array String := #[]
  for c in children do
    let some info := (← getEnv).find? c.decl
      | why := why.push s!"{c.node}: {c.decl} is not declared"; continue
    let us ← info.levelParams.mapM fun _ => mkFreshLevelMVar
    let ty ← instantiateTypeLevelParams info.toConstantVal us
    let (mvars, names, stagesOf) ← stages lctx ty
    let mut found : Option Expr := none
    for (k, body) in stagesOf do
      let saved ← saveState
      if ← isDefEq body goal then
        let args := mvars.extract 0 k
        if ← fillAll locals args names 0 constructDepth (pure true) then
          let e ← instantiateMVars (mkAppN (.const c.decl us) args)
          if !e.hasExprMVar then
            found := some (← instantiateLevelMVars e)
            break
      saved.restore
    match found with
    | some e => return .ok (c.node, e)
    | none => why := why.push s!"{c.node}: its statement is not this hole at any depth, or nothing in scope fills it"
  return .error why
where
  instantiateLevelMVars (e : Expr) : MetaM Expr := do
    let e ← instantiateMVars e
    -- a universe left open by the unification is not a choice the proof depends on
    return e.replaceLevel fun l => if l.hasMVar then some levelZero else none

/-- What one hole became. -/
structure Joined where
  hole : String
  child : String

/-- The assembly's term with every hole replaced (F28-T7). -/
partial def joinExpr (children : Array Child) (e : Expr) : StateT (Array Joined) MetaM Expr := do
  match e with
  | .letE n t v b nondep =>
    let t' ← joinExpr children t
    let v' ← if isSorry v then do
        match ← fillHole (← instantiateMVars t') children with
        | .ok (node, term) =>
          modify fun (acc : Array Joined) => acc.push { hole := n.toString, child := node }
          pure term
        | .error why =>
          throwError "hole {n}: no child closes it: {"; ".intercalate why.toList}"
      else joinExpr children v
    withLetDecl n t' v' (nondep := nondep) fun x => do
      let b' ← joinExpr children (b.instantiate1 x)
      mkLetFVars (generalizeNondepLet := false) #[x] b'
  | .lam n d b bi =>
    let d' ← joinExpr children d
    withLocalDecl n bi d' fun x => do mkLambdaFVars #[x] (← joinExpr children (b.instantiate1 x))
  | .forallE n d b bi =>
    let d' ← joinExpr children d
    withLocalDecl n bi d' fun x => do mkForallFVars #[x] (← joinExpr children (b.instantiate1 x))
  | .app f a => return mkApp (← joinExpr children f) (← joinExpr children a)
  | .mdata m b => return .mdata m (← joinExpr children b)
  | .proj s i b => return .proj s i (← joinExpr children b)
  | e =>
    if isSorry e then throwError "a hole that is not the value of a `have`"
    return e

/-- The constants of `env`'s own module that `e` reaches, transitively, other than `skip`. -/
partial def localClosure (env : Environment) (e : Expr) (skip : Name) : Array ConstantInfo :=
  Id.run do
    let isLocal (n : Name) : Bool := (env.getModuleIdxFor? n).isNone
    let mut seen : NameSet := {}
    let mut out : Array ConstantInfo := #[]
    let mut todo : Array Name := e.getUsedConstants
    while !todo.isEmpty do
      let n := todo.back!
      todo := todo.pop
      if seen.contains n || n == skip || !isLocal n then continue
      seen := seen.insert n
      if let some c := env.find? n then
        out := out.push c
        todo := todo ++ c.type.getUsedConstants
        if let some v := c.value? (allowOpaque := true) then todo := todo ++ v.getUsedConstants
    return out

def jsonOf (joined : Array Joined) : Json :=
  Json.arr (joined.map fun j => Json.mkObj [("hole", Json.str j.hole), ("child", Json.str j.child)])

/-- The whole run: elaborate, join, kernel-check, write. -/
def run (path : System.FilePath) (moduleName decl : Name) (children : Array Child)
    (outOlean : System.FilePath) : IO Json := do
  let input ← IO.FS.readFile path
  let inputCtx := Parser.mkInputContext input path.toString
  let (stx, parserState, messages) ← Parser.parseHeader inputCtx
  let (env0, messages) ← processHeader stx {} messages inputCtx (mainModule := moduleName)
  let s ← IO.processCommands inputCtx parserState (Command.mkState env0 messages {})
  let env1 := s.commandState.env
  if s.commandState.messages.hasErrors then
    let errs := ((← messagesToArray s.commandState.messages).filter (·.severity == "error")).map (·.text)
    throw <| IO.userError s!"assembly does not elaborate: {"; ".intercalate errs.toList}"
  let some info := env1.find? decl | throw <| IO.userError s!"{decl} is not declared in {path}"
  let some value := info.value? (allowOpaque := true)
    | throw <| IO.userError s!"{decl} has no value"
  let coreCtx : Core.Context := { fileName := path.toString, fileMap := inputCtx.fileMap,
                                  maxHeartbeats := 0 }
  let ((joined, holes), _, _) ←
    ((joinExpr children value).run #[] : MetaM (Expr × Array Joined)).toIO coreCtx { env := env1 }
  if holes.isEmpty then throw <| IO.userError s!"{decl} has no hole to join"
  if joined.hasSorry then throw <| IO.userError "the joined term still contains sorry"
  -- the statement's imports, the assembly's helpers and matchers the term reaches, then the theorem
  let aux := localClosure env1 joined decl
  let env2 ← replayInto env0 aux
  let d := Declaration.thmDecl { name := decl, levelParams := info.levelParams, type := info.type,
                                 value := joined }
  -- `addDecl` sends the declaration to the kernel; a refusal is the join's failure
  let (axioms, coreState) ← (do addDecl d; collectAxioms decl : CoreM (Array Name)).toIO coreCtx
    { env := env2 }
  let env3 := coreState.env
  if axioms.contains ``sorryAx then throw <| IO.userError "the joined theorem depends on sorryAx"
  if let some dir := outOlean.parent then IO.FS.createDirAll dir
  writeModule env3 outOlean
  return Json.mkObj [("ok", Json.bool true), ("decl", Json.str decl.toString),
    ("holes", jsonOf holes), ("axioms", toJson (axioms.map toString)),
    ("olean", Json.str outOlean.toString)]
end OpnGate.Close
