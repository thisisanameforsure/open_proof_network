import OpnGate.Frontend
import OpnGate.UsedConstants
import OpnGate.Compiled

/-!
`opn-used-constants --module <Name> --decl <Name>` (the gate's step 8, F02-T12)
`opn-used-constants --file <Statement.lean> --module <Name> --decl <Name>` (a statement of record)

Prints `{"ok": true, "decl": ..., "constants": [{"name", "module"}], "axioms": [...]}`.

**Without `--file`** the declaration is read from the compiled module `--module`, which the gate's
step 4 has replayed through the kernel: it is imported with initializers off and without extension
data, so nothing of it runs here (F02-T12), and the axioms are walked through the constant table
(`axiomsOf`), never read from data the module carries. The module's own declarations are the ones
recursed through and reported as the submission's (`module: null`).

**With `--file`** the file is elaborated, as before: only ever a statement of record, never a
contributor's proof (the products' library tags, F03-R6, and the statement QA's grounding, F12).
-/
open Lean Elab OpnGate

/-- Step 8: the compiled module, read and never run. -/
def compiledFootprint (modStr declStr : String) : IO UInt32 := do
  let declName := declStr.toName
  let env ← importModules #[{ module := modStr.toName }] {} (loadExts := false)
  let some idx := env.getModuleIdxFor? declName
    | fail s!"module {modStr} does not declare {declStr}"
  unless env.header.moduleNames[idx.toNat]! == modStr.toName do
    return ← fail s!"{declStr} is declared by {env.header.moduleNames[idx.toNat]!}, not {modStr}"
  let consts := usedConstantsOwnedBy env declName modStr.toName
  match axiomsOf env declName with
  | .error e => fail e
  | .ok axioms =>
    printJson <| Json.mkObj [
      ("ok", Json.bool true), ("decl", Json.str declStr),
      ("constants", toJson consts), ("axioms", toJson axioms)]
    return 0

/-- A statement of record, elaborated here. -/
def elaboratedFootprint (path modStr declStr : String) : IO UInt32 := do
  let declName := declStr.toName
  let (env, log) ← elabFile path modStr.toName
  if let some code ← failIfErrors "file" log then return code
  if env.find? declName |>.isNone then
    return ← fail s!"declaration {declStr} not found in {path}"
  let consts := usedConstants env declName
  let ctx : Core.Context := { fileName := path, fileMap := default }
  let (axioms, _) ← (collectAxioms declName : CoreM (Array Name)).toIO ctx { env }
  printJson <| Json.mkObj [
    ("ok", Json.bool true), ("decl", Json.str declStr),
    ("constants", toJson consts), ("axioms", toJson (axioms.map toString))]
  return 0

unsafe def main (args : List String) : IO UInt32 := do
  let file? := getArg (parseArgs args).1 "file"
  -- F02-T12: reading a compiled module needs no initializer, so none is enabled.
  runMain args (initializers := file?.isSome) do
    let (kv, _) := parseArgs args
    let some modStr := getArg kv "module" | fail "missing --module"
    let some declStr := getArg kv "decl" | fail "missing --decl"
    match file? with
    | some path => elaboratedFootprint path modStr declStr
    | none => compiledFootprint modStr declStr
