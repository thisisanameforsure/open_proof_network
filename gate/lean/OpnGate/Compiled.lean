import Lean

/-!
Reading a contributor's compiled module without executing any of it (F02-T11, T12).

A judging program must not run code a contributor wrote, because anything that runs in its
process can print, or forge, the verdict. Elaborating a contributor's file runs its `#eval`,
`run_cmd`, macros and elaborators; importing its compiled module with extensions loaded runs its
`initialize` blocks. So the judging programs never do either. They read the module's olean as
data (`readModuleData`: constants and the names it imports, nothing executed) and do one of two
things with it:

* **import it without extensions** (`importModules … (loadExts := false)` with initializers
  off): the environment is the constant table and nothing else. Enough for a program that only
  walks constants or asks the kernel (`opn-statement-meaning`, `opn-axioms`, `opn-used-constants`,
  `opn-artifact-type` on a counterexample or a vacuity certificate), and only for a module the
  step-4 kernel replay has already re-checked;
* **replay its constants into a trusted environment** (`replayInto`): the environment is imported
  from modules no contributor process produced (the toolchain, Mathlib, and the graph's admitted
  files compiled by the gate in the judging directory), with their extensions, so pretty-printing,
  notations and `Meta.isDefEq` behave exactly as when the file was elaborated there; and each of
  the contributor's constants is added through the kernel, which checks it, as
  `Lean.Environment.replay` does (Lean 4.33 `Lean/Replay.lean`, ported here because that function
  answers a kernel environment the elaborator's `find?` cannot see). No constant's code runs: a
  declaration's value is a term the kernel type-checks, never a program the interpreter executes.

The olean itself is still a file the contributor's compile produced and the reader trusts its
format, as the kernel replay (`leanchecker`) and every Lean import does.
-/
open Lean

namespace OpnGate

/-- A module's constants and the modules it imports, read from its olean; nothing executed. -/
def readOlean (path : System.FilePath) : IO (Array ConstantInfo × Array Name) := do
  unless ← path.pathExists do
    throw <| IO.userError s!"no compiled module at {path}"
  let (data, _) ← readModuleData path
  return (data.constants, data.imports.map (·.module))

namespace Replay

structure State where
  env : Environment
  remaining : NameSet := {}
  pending : NameSet := {}
  ctors : NameSet := {}
  recs : NameSet := {}

abbrev M := ReaderT (Std.HashMap Name ConstantInfo) <| StateRefT State IO

def isTodo (n : Name) : M Bool := do
  let s ← get
  if s.remaining.contains n then
    set { s with remaining := s.remaining.erase n, pending := s.pending.insert n }
    return true
  return false

/-- Add a declaration through the kernel (`doCheck := true`): a declaration the kernel rejects
is an error, never a constant of the environment. -/
def addDecl (d : Declaration) : M Unit := do
  match (← get).env.addDeclCore 0 0 d none with
  | .ok env => modify fun s => { s with env }
  | .error ex =>
    throw <| IO.userError s!"the kernel rejected a declaration: {← (ex.toMessageData {}).toString}"

mutual
partial def replayConstant (name : Name) : M Unit := do
  unless ← isTodo name do return
  let some ci := (← read)[name]? | return
  replayConstants ci.getUsedConstantsAsSet
  unless (← get).pending.contains name do return
  try
    match ci with
    | .defnInfo info => addDecl (.defnDecl info)
    | .thmInfo info =>
      -- As `Lean.Environment.replay`: a theorem already present with the same name, type and
      -- universe parameters is the same proposition, and is not added twice. This is how a
      -- dependency's proof meets the signature its `Context.lean` restates.
      if let some (.thmInfo old) := (← get).env.find? ci.name then
        if old.type == info.type && old.levelParams == info.levelParams then
          modify fun s => { s with pending := s.pending.erase name }
          return
      addDecl (.thmDecl info)
    | .axiomInfo info => addDecl (.axiomDecl info)
    | .opaqueInfo info => addDecl (.opaqueDecl info)
    | .inductInfo info =>
      let consts ← read
      let all := info.all.filterMap (consts[·]?)
      for o in all do
        modify fun s => { s with remaining := s.remaining.erase o.name,
                                 pending := s.pending.erase o.name }
      let mut types : List InductiveType := []
      for o in all do
        let ctors := o.inductiveVal!.ctors.filterMap (consts[·]?)
        for c in ctors do replayConstants c.getUsedConstantsAsSet
        types := types ++ [{ name := o.name, type := o.type,
                             ctors := ctors.map fun c => { name := c.name, type := c.type } }]
      addDecl (.inductDecl info.levelParams info.numParams types false)
    | .ctorInfo info => modify fun s => { s with ctors := s.ctors.insert info.name }
    | .recInfo info => modify fun s => { s with recs := s.recs.insert info.name }
    | .quotInfo _ => throw <| IO.userError "a contributor module may not declare the quotient"
    modify fun s => { s with pending := s.pending.erase name }
  catch ex =>
    throw <| IO.userError s!"while replaying {name}: {ex}"

partial def replayConstants (names : NameSet) : M Unit := do
  for n in names do replayConstant n
end

end Replay

/-- `consts` (one module's, as `readOlean` gives them) added to `env` through the kernel, in
dependency order. Unsafe and `partial` constants are left out, as `Lean.Environment.replay`
leaves them: no theorem can use one, and a term that names one then names a missing constant.
Constructors and recursors are not sent to the kernel; each must be exactly the one the kernel
generated for its inductive. Nothing is executed. -/
def replayInto (env : Environment) (consts : Array ConstantInfo) : IO Environment := do
  let mut map : Std.HashMap Name ConstantInfo := {}
  let mut remaining : NameSet := {}
  for c in consts do
    map := map.insert c.name c
    if !c.isUnsafe && !c.isPartial then remaining := remaining.insert c.name
  let (_, s) ← (do
      for n in remaining do Replay.replayConstant n
      : Replay.M Unit).run map |>.run { env, remaining }
  let kenv := s.env.toKernelEnv
  for n in s.ctors do
    match kenv.find? n, map[n]? with
    | some (.ctorInfo a), some (.ctorInfo b) =>
      unless a == b do throw <| IO.userError s!"constructor {n} is not the one its type generates"
    | _, _ => throw <| IO.userError s!"no such constructor {n}"
  for n in s.recs do
    match kenv.find? n, map[n]? with
    | some (.recInfo a), some (.recInfo b) =>
      unless a == b do throw <| IO.userError s!"recursor {n} is not the one its type generates"
    | _, _ => throw <| IO.userError s!"no such recursor {n}"
  return s.env

/-- The contributor modules a compiled module reaches, read as data (F02-T13). -/
structure Closure where
  /-- Each graph module with its constants, every module after the graph modules it imports;
  the start module last. -/
  modules : Array (Name × Array ConstantInfo) := #[]
  /-- Every module outside the graph that any of them imports, in the order first met: these are
  imported, with their extensions, from the search path (the toolchain, Mathlib and the gate's
  own build of the record), and never from where the graph modules were read. -/
  external : Array Name := #[]
  seen : NameSet := {}

/-- Walk `start`'s imports (its olean at `path`), reading each import `isGraph` accepts from
`dir` by path (`modToFilePath`) and collecting every other one as external. Nothing is imported
or executed: each olean is read with `readOlean`. A module met twice is read once; an import
cycle, which no compile can produce, then leaves a module before one it needs, and the kernel
replay that follows fails on the missing constant. -/
partial def graphClosure (dir : System.FilePath) (isGraph : Name → Bool) (start : Name)
    (path : System.FilePath) : IO Closure := do
  let rec visit (m : Name) (p : System.FilePath) : StateRefT Closure IO Unit := do
    if (← get).seen.contains m then return
    modify fun s => { s with seen := s.seen.insert m }
    let (consts, imports) ← readOlean p
    for i in imports do
      if isGraph i then
        visit i (modToFilePath dir i "olean")
      else unless (← get).external.contains i do
        modify fun s => { s with external := s.external.push i }
    modify fun s => { s with modules := s.modules.push (m, consts) }
  let ((), closure) ← (visit start path).run {}
  return closure

/-- Every axiom `root` reaches through the types and values of the constants it names, in name
order, or the first constant that is not in `env` (F02-T11: walked here, never read from data an
imported module carries). -/
partial def axiomsOf (env : Environment) (root : Name) : Except String (Array String) :=
  Id.run do
    let mut seen : NameSet := {}
    let mut todo : List Name := [root]
    let mut found : Array String := #[]
    while true do
      match todo with
      | [] => break
      | n :: rest =>
        todo := rest
        if seen.contains n then continue
        seen := seen.insert n
        let some info := env.find? n
          | return .error s!"constant {n} is not in the environment"
        if info.isAxiom then found := found.push n.toString
        for c in info.getUsedConstantsAsSet.toList do
          todo := c :: todo
    return .ok (found.qsort (· < ·))

/-- The statement module's own constants that `start` reaches, through their types and values. -/
partial def localClosure (locals : Std.HashMap Name ConstantInfo) (start : Expr) : Array Name :=
  Id.run do
    let mut seen : NameSet := {}
    let mut out : Array Name := #[]
    let mut todo : List Name := start.getUsedConstants.toList
    while true do
      match todo with
      | [] => break
      | n :: rest =>
        todo := rest
        if seen.contains n then continue
        seen := seen.insert n
        let some info := locals[n]? | continue
        out := out.push n
        for c in info.getUsedConstantsAsSet.toList do
          todo := c :: todo
    return out.qsort (·.toString < ·.toString)

/-- Whether two declarations of one name are the same declaration: kind, universe parameters,
type and value, as terms. -/
def sameDeclaration (a b : ConstantInfo) : Bool :=
  a.levelParams == b.levelParams && a.type == b.type
    && a.value? (allowOpaque := true) == b.value? (allowOpaque := true)
    && a.isTheorem == b.isTheorem && a.isDefinition == b.isDefinition
    && a.isAxiom == b.isAxiom && a.isInductive == b.isInductive && a.isCtor == b.isCtor

/-- Each constant of `locals` (a statement module's own) that `type` reaches and that `env` does
not hold as the same declaration, by name. -/
def localMismatch (locals : Std.HashMap Name ConstantInfo) (env : Environment) (type : Expr)
    : Array Name × Array String := Id.run do
  let reached := localClosure locals type
  let mut mismatch : Array String := #[]
  for name in reached do
    let some own := locals[name]? | continue
    match env.find? name with
    | some theirs => unless sameDeclaration own theirs do mismatch := mismatch.push name.toString
    | none => mismatch := mismatch.push name.toString
  return (reached, mismatch)

end OpnGate
