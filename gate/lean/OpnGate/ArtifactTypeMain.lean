import OpnGate.Frontend
import OpnGate.ArtifactType
import OpnGate.Holes
import OpnGate.Compiled

/-!
`opn-artifact-type --statement <Statement.lean> --module <Name> --decl <Name>
                  --artifact <file.lean> --artifact-module <Name> --artifact-decl <Name>
                  --kind proof|counterexample|vacuity|partial|reduction`

`opn-artifact-type --statement-olean <Statement.olean> --decl <Name>
                  --artifact-module <Name> --artifact-decl <Name> --kind <kind>
                  [--artifact-olean <Proof.olean> --modules <dir>]`   (the compiled forms)

**The gate calls only the compiled forms** (F02-T12, T13): a counterexample's or vacuity
certificate's module is imported without extensions (`compiledJudgment`); a partial's or a
reduction's assembly, and the graph modules it reaches, are read from `--modules` as data and
added through the kernel into an environment imported from modules of record
(`compiledHoleJudgment`). Nothing of the contributor's runs in this process in either. The
elaborating form below (`--statement`, `--artifact`) is kept as the reference the lean tier's
golden was made with and compares the compiled form against; no gate step calls it, because
elaborating the artifact here runs its `#eval`s and its imports' `initialize` blocks beside the
verdict.

Prints `{"ok": true, "kind", "expected", "declared", "matches", "axioms", "holes", "unnamed",
"body_is_hole"}` (F07-R4, R5).

The two files are elaborated independently and compared in the artifact's environment. They
cannot share one environment the way a statement and its witness do (F01-R3), because a partial
proof declares the statement's own name: putting both in one environment is a duplicate
declaration, not a comparison. Comparing across the two is sound here because the statement's
type mentions only constants from the imports both files share — and if it ever mentions one the
artifact does not import, the comparison fails, which is the right answer.

`--siblings <manifest.json>` (F07-T7, optional) names the target's other statements, each staged
by the gate as a probe: imports removed and the theorem renamed, so elaborating it on these imports
never redeclares a name the artifact's environment already holds. The manifest is a JSON array of
`{"node", "file", "decl"}`, `file` relative to the manifest. Each hole then reports
`defeq_sibling`, the first node whose statement it is. A probe that does not elaborate here cannot
be what a hole restates, so it is skipped and never fails the check.

`--ancestors <manifest.json>` (F07-T34, optional) names the node's ancestors — every node that
depends on it, nearest first — staged and read exactly as the siblings are. Each hole then reports
`defeq_ancestor`, the first ancestor whose statement it is, which the gate refuses as a cycle. An
ancestor's probe that does not elaborate on these imports is skipped: a hole elaborated on the same
imports cannot be definitionally equal to a statement that needs constants they do not hold.
-/
open Lean Meta Elab OpnGate

/-- One sibling's statement type, or `none` when its probe does not elaborate on `base`. -/
def siblingType (base : Environment) (path : System.FilePath) (node decl : String)
    : IO (Option (String × Expr)) := do
  try
    let (env, log) ← elabFile path `OpnGate.SiblingProbe (some base)
    if log.hasErrors then return none
    return (env.find? decl.toName).map fun info => (node, info.type)
  catch _ => return none

/-- The sibling statements a manifest names, in its order. -/
def siblingTypes (manifest : System.FilePath) (base : Environment)
    : IO (Array (String × Expr)) := do
  let dir := manifest.parent.getD "."
  let json ← IO.ofExcept (Json.parse (← IO.FS.readFile manifest))
  let entries ← IO.ofExcept json.getArr?
  let mut out := #[]
  for entry in entries do
    match entry.getObjValAs? String "node", entry.getObjValAs? String "file",
        entry.getObjValAs? String "decl" with
    | .ok node, .ok file, .ok decl =>
      if let some found ← siblingType base (dir / file) node decl then
        out := out.push found
    | _, _, _ => pure ()
  return out

/-- F02-T12, F08-T29b: an artifact with no holes, judged from compiled modules only. -/
def compiledJudgment (kv : List (String × String)) (oleanPath : String) : IO UInt32 := do
  let some stmtDecl := getArg kv "decl" | fail "missing --decl"
  let some artMod := getArg kv "artifact-module" | fail "missing --artifact-module"
  let some artDecl := getArg kv "artifact-decl" | fail "missing --artifact-decl"
  let some kindStr := getArg kv "kind" | fail "missing --kind"
  let some kind := ArtifactKind.ofString? kindStr
    | fail s!"unknown artifact kind {kindStr}"
  unless kind == .proof || kind == .counterexample || kind == .vacuity do
    return ← fail s!"a {kind.toString}'s holes are read by compiledHoleJudgment"
  let (stmtConsts, _) ← readOlean oleanPath
  let mut locals : Std.HashMap Name ConstantInfo := {}
  for info in stmtConsts do
    locals := locals.insert info.name info
  let some stmtInfo := locals[stmtDecl.toName]?
    | fail s!"declaration {stmtDecl} not found in {oleanPath}"
  let env ← importModules #[{ module := artMod.toName }] {} (loadExts := false)
  let some idx := env.getModuleIdxFor? artDecl.toName
    | fail s!"module {artMod} does not declare {artDecl}"
  unless env.header.moduleNames[idx.toNat]! == artMod.toName do
    return ← fail s!"{artDecl} is declared by {env.header.moduleNames[idx.toNat]!}, not {artMod}"
  let some artInfo := env.find? artDecl.toName
    | fail s!"module {artMod} does not declare {artDecl}"
  let ctx : Core.Context := { fileName := "<opn-artifact-type>", fileMap := default }
  let state : Core.State := { env }
  let (expected, _, _) ← (expectedArtifactType kind stmtInfo.type : MetaM Expr).toIO ctx state
  let (_, mismatch) := localMismatch locals env stmtInfo.type
  let defeq := stmtInfo.levelParams == artInfo.levelParams
    && (expected == artInfo.type || Kernel.isDefEqGuarded env {} expected artInfo.type)
  let show_ (e : Expr) : IO String := do
    try
      let (fmt, _) ← (Meta.ppExpr e).run'.toIO ctx state
      return toString fmt
    catch _ => return toString e
  match axiomsOf env artDecl.toName with
  | .error e => fail e
  | .ok axioms =>
    printJson <| Json.mkObj [
      ("ok", Json.bool true),
      ("kind", Json.str kind.toString),
      ("decl", Json.str artDecl),
      ("expected", Json.str (← show_ expected)),
      ("declared", Json.str (← show_ artInfo.type)),
      ("matches", Json.bool (defeq && mismatch.isEmpty)),
      ("local_mismatch", toJson mismatch),
      ("axioms", toJson axioms),
      ("holes", Json.arr #[]),
      ("unnamed", Json.num 0),
      ("body_is_hole", Json.bool false)]
    return 0

/-- Whether a module is the graph's: read from the modules directory as data and replayed, never
imported. Every contributor module is one (a node's `Proof` and generated `Context`); the target's
definitions (`Defs.*`) are imported from the gate's own build of the record. -/
def isGraphModule (m : Name) : Bool := m.getRoot == `Nodes

/-- `(f : IO α)`'s value, or its error as a string. -/
def attempt {α : Type} (f : IO α) : IO (Except String α) := do
  try return .ok (← f) catch e => return .error (toString e)

/-- F02-T13: a partial's (or a reduction's) holes, read from compiled modules.

The environment is imported, with its extensions, from modules of record only: `Init`, and
every module outside the graph that the assembly or any graph module it reaches imports (the
toolchain's, Mathlib's, the target's `Defs.*` from the gate's build in the judging directory),
found on the search path, which holds no contributor module. Then the graph modules the assembly
reaches (the deps' and uses' `Proof` modules, the generated `Context`s), read by path from
`--modules`, are added constant by constant through the kernel in dependency order (`replayInto`),
and then the assembly (`--artifact-olean`). No contributor module is imported, so none of its
`initialize` blocks runs, and none is elaborated, so no `#eval`, macro or elaborator of it runs:
the hole report below is computed by this program alone.

The siblings and ancestors are statement text of record (staged probes), elaborated on the
environment before the assembly is added, as they were elaborated on the assembly's imports
before. `holeReport`, the type comparison and the printing are the elaborating form's, unchanged.

What a replayed constant does not carry is its extension entries (an `instance`, `notation`,
`@[simp]`, `@[reducible]`, a `match` compilation's matcher info): only Init's, Mathlib's and the
definitions' are loaded, because an entry is the contributor's data and some (an unexpander, a
delaborator) are the contributor's code. So a hole whose type mentions one of the assembly's own
constants (other than the statement's) is reported `closed_roundtrip: false`: a matcher would
print as its constant and read back here, where the constant is, and nowhere a child's statement
is elaborated (before T13 it printed as `match` and did not read back either). A hole whose
printed type needs an instance or notation a dep proof declared does not read back, and is
refused the same way; it is never written wrong. -/
def compiledHoleJudgment (kv : List (String × String)) (oleanPath : String) (kind : ArtifactKind)
    : IO UInt32 := do
  let some stmtDecl := getArg kv "decl" | fail "missing --decl"
  let some artMod := getArg kv "artifact-module" | fail "missing --artifact-module"
  let some artDecl := getArg kv "artifact-decl" | fail "missing --artifact-decl"
  let some artOlean := getArg kv "artifact-olean" | fail "missing --artifact-olean"
  let some modulesDir := getArg kv "modules" | fail "missing --modules"
  let artName := artMod.toName
  let declName := artDecl.toName
  unless isGraphModule artName do
    return ← fail s!"{artMod} is not a graph module"
  let (stmtConsts, _) ← readOlean oleanPath
  let some stmtInfo := stmtConsts.find? (·.name == stmtDecl.toName)
    | fail s!"declaration {stmtDecl} not found in {oleanPath}"
  let closure ← graphClosure modulesDir isGraphModule artName artOlean
  let some (_, artConsts) := closure.modules.find? (·.1 == artName)
    | fail s!"no compiled module {artMod}"
  unless artConsts.any (·.name == declName) do
    return ← fail s!"{artMod} does not declare {artDecl}"
  let imports := #[`Init] ++ closure.external.filter (· != `Init)
  let mut base ← importModules (imports.map ({ module := · })) {} (loadExts := true)
  for (m, consts) in closure.modules do
    if m == artName then continue
    match ← attempt (replayInto base consts) with
    | .ok env => base := env
    | .error e => return ← fail s!"artifact does not elaborate: module {m}: {e}"
  -- The declaration is the assembly's: a module it imports may not have supplied it already.
  if base.contains declName then
    return ← fail s!"{artDecl} is declared by a module {artMod} imports, not by {artMod}"
  let siblings ← match getArg kv "siblings" with
    | some manifest => siblingTypes manifest base
    | none => pure #[]
  let ancestors ← match getArg kv "ancestors" with
    | some manifest => siblingTypes manifest base
    | none => pure #[]
  let artEnv ← match ← attempt (replayInto base artConsts) with
    | .ok env => pure (env.setMainModule artName)
    | .error e => return ← fail s!"artifact does not elaborate: {e}"
  let some artInfo := artEnv.find? declName
    | fail s!"{artMod} does not declare {artDecl}"
  -- The assembly's own constants that are not the statement's: replayed without the extension
  -- entries that printed them as source (a matcher prints as its constant, not as `match`), and
  -- in no environment a child's statement is elaborated in. A hole naming one is no round trip.
  let stmtNames := stmtConsts.foldl (fun s c => s.insert c.name) (NameSet.empty)
  let foreign := artConsts.foldl
    (fun s c => if stmtNames.contains c.name then s else s.insert c.name) (NameSet.empty)
  let ctx : Core.Context := { fileName := artMod, fileMap := default }
  let state : Core.State := { env := artEnv }
  let ((expectedStr, declaredStr, typeMatches, holes), _, _) ← (do
      let expected ← expectedArtifactType kind stmtInfo.type
      let ok ← withReducible (isDefEq expected artInfo.type) <||> isDefEq expected artInfo.type
      let holes ← match artInfo.value? (allowOpaque := true) with
        | some value => holeReport stmtInfo.type value siblings ancestors foreign
        | none => pure { holes := #[], unnamed := 0, body_is_hole := false }
      return (toString (← ppExpr expected), toString (← ppExpr artInfo.type), ok, holes)
      : TermElabM (String × String × Bool × HoleReport)).run'.toIO ctx state
  match axiomsOf artEnv declName with
  | .error e => fail e
  | .ok axioms =>
    printJson <| Json.mkObj [
      ("ok", Json.bool true),
      ("kind", Json.str kind.toString),
      ("decl", Json.str artDecl),
      ("expected", Json.str expectedStr),
      ("declared", Json.str declaredStr),
      ("matches", Json.bool typeMatches),
      ("axioms", toJson axioms),
      ("holes", toJson holes.holes),
      ("unnamed", Json.num holes.unnamed),
      ("body_is_hole", Json.bool holes.body_is_hole)]
    return 0

/-- The compiled form for a kind with holes: its environment imports modules of record with their
extensions, so initializers are enabled; no contributor module is imported. -/
def holeKind (kv : List (String × String)) : Option ArtifactKind :=
  match (getArg kv "kind").bind ArtifactKind.ofString? with
  | some .partial_ => some .partial_
  | some .reduction => some .reduction
  | _ => none

unsafe def main (args : List String) : IO UInt32 :=
  let kv0 := (parseArgs args).1
  let olean? := getArg kv0 "statement-olean"
  -- F02-T12: the compiled form of a hole-free artifact imports the artifact's module without
  -- extensions, so no initializer is enabled. F02-T13: the compiled form of a partial imports
  -- modules of record only, with their extensions (and so their initializers).
  runMain args (initializers := olean?.isNone || (holeKind kv0).isSome) do
  let (kv, _) := parseArgs args
  if let some oleanPath := olean? then
    if let some kind := holeKind kv then
      return ← compiledHoleJudgment kv oleanPath kind
    return ← compiledJudgment kv oleanPath
  let some stmtPath := getArg kv "statement" | fail "missing --statement"
  let some stmtMod := getArg kv "module" | fail "missing --module"
  let some stmtDecl := getArg kv "decl" | fail "missing --decl"
  let some artPath := getArg kv "artifact" | fail "missing --artifact"
  let some artMod := getArg kv "artifact-module" | fail "missing --artifact-module"
  let some artDecl := getArg kv "artifact-decl" | fail "missing --artifact-decl"
  let some kindStr := getArg kv "kind" | fail "missing --kind"
  let some kind := ArtifactKind.ofString? kindStr
    | fail s!"unknown artifact kind {kindStr}"

  -- Import once, then elaborate each file's commands on its own copy of that environment.
  let (base, baseLog) ← unionHeaderEnv #[stmtPath, artPath] stmtMod.toName
  if let some code ← failIfErrors "imports" baseLog then return code

  let (stmtEnv, stmtLog) ← elabFile stmtPath stmtMod.toName (some base)
  if let some code ← failIfErrors "statement" stmtLog then return code
  let some stmtInfo := stmtEnv.find? stmtDecl.toName
    | fail s!"declaration {stmtDecl} not found in {stmtPath}"

  let (artEnv, artLog) ← elabFile artPath artMod.toName (some base)
  if let some code ← failIfErrors "artifact" artLog then return code
  let some artInfo := artEnv.find? artDecl.toName
    | fail s!"{artPath} does not declare {artDecl}"
  let siblings ← match getArg kv "siblings" with
    | some manifest => siblingTypes manifest base
    | none => pure #[]
  let ancestors ← match getArg kv "ancestors" with
    | some manifest => siblingTypes manifest base
    | none => pure #[]

  let ctx : Core.Context := { fileName := artPath, fileMap := default }
  let state : Core.State := { env := artEnv }
  let ((expectedStr, declaredStr, typeMatches, holes), _, _) ← (do
      let expected ← expectedArtifactType kind stmtInfo.type
      let ok ← withReducible (isDefEq expected artInfo.type) <||> isDefEq expected artInfo.type
      -- `allowOpaque := true`: a theorem's proof term is opaque for reduction, and this is the
      -- one place that wants to look at it rather than use it.
      let holes ← match artInfo.value? (allowOpaque := true) with
        | some value => holeReport stmtInfo.type value siblings ancestors
        | none => pure { holes := #[], unnamed := 0, body_is_hole := false }
      return (toString (← ppExpr expected), toString (← ppExpr artInfo.type), ok, holes)
      -- `TermElabM` rather than `MetaM`: a hole's printed type is elaborated back and compared
      -- with the obligation it came from (F07-R19), and reading a type from source is term
      -- elaboration. Nothing else in the block needs it; `MetaM` actions lift unchanged.
      : TermElabM (String × String × Bool × HoleReport)).run'.toIO ctx state
  let (axioms, _) ← (collectAxioms artDecl.toName : CoreM (Array Name)).toIO ctx state

  printJson <| Json.mkObj [
    ("ok", Json.bool true),
    ("kind", Json.str kind.toString),
    ("decl", Json.str artDecl),
    ("expected", Json.str expectedStr),
    ("declared", Json.str declaredStr),
    ("matches", Json.bool typeMatches),
    ("axioms", toJson (axioms.map toString)),
    ("holes", toJson holes.holes),
    ("unnamed", Json.num holes.unnamed),
    ("body_is_hole", Json.bool holes.body_is_hole)]
  return 0
