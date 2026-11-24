import Lean

/-!
One process, one import: elaborate every listed target's `defs/` modules (in order) and its root
statement on top of the union of their library imports, under Lean's default options and again
with `autoImplicit` and `relaxedAutoImplicit` off (the registry's own lakefile settings).

Usage: lean --run Strict.lean <manifest.json>
manifest: {"imports": [module...], "targets": [{"id", "modules": [{"name","path"}], "statement"}]}
Prints one JSON line per target.
-/
open Lean Elab

def errorsOf (log : MessageLog) : IO (Array String) := do
  let mut out := #[]
  for m in log.toList do
    if m.severity == .error then
      out := out.push s!"{m.pos.line}:{m.pos.column}: {← m.data.toString}"
  return out

/-- Elaborate `path`'s commands (its import header skipped; the union env already holds every
library import, and earlier `Defs` modules are already elaborated into `env`). -/
def elabOn (env : Environment) (path : String) (moduleName : Name) (opts : Options)
    : IO (Environment × Array String) := do
  let input ← IO.FS.readFile path
  let inputCtx := Parser.mkInputContext input path
  let (_, parserState, messages) ← Parser.parseHeader inputCtx
  let s ← IO.processCommands inputCtx parserState
    (Command.mkState (env.setMainModule moduleName) messages opts)
  return (s.commandState.env, ← errorsOf s.commandState.messages)

def baseOpts : Options :=
  ({} : Options).set `maxHeartbeats (1000000 : Nat)

def strictOpts : Options :=
  (baseOpts.setBool `autoImplicit false).setBool `relaxedAutoImplicit false

def jstr (j : Json) (k : String) : String := (j.getObjValAs? String k).toOption.getD ""

unsafe def main (args : List String) : IO UInt32 := do
  let some manifestPath := args.head? | throw <| IO.userError "manifest path required"
  enableInitializersExecution
  initSearchPath (← findSysroot)
  let manifest ← IO.ofExcept <| Json.parse (← IO.FS.readFile manifestPath)
  let imports : Array Json := (manifest.getObjValAs? (Array Json) "imports").toOption.getD #[]
  let header := String.join (imports.toList.map fun j => s!"import {j.getStr?.toOption.getD ""}\n")
  let inputCtx := Parser.mkInputContext header "<union>"
  let (stx, _, msgs) ← Parser.parseHeader inputCtx
  let (base, hmsgs) ← processHeader stx {} msgs inputCtx (mainModule := `Strict)
  let herrs ← errorsOf hmsgs
  unless herrs.isEmpty do
    IO.eprintln s!"header errors: {herrs}"
    return 1
  let targets : Array Json := (manifest.getObjValAs? (Array Json) "targets").toOption.getD #[]
  -- env after a given ordered prefix of modules, keyed by the prefix's content hashes
  let mut cache : Std.HashMap String (Environment × Array Json) := {}
  for t in targets do
    let tid := jstr t "id"
    let modules : Array Json := (t.getObjValAs? (Array Json) "modules").toOption.getD #[]
    let mut env := base
    let mut key := ""
    let mut modReports : Array Json := #[]
    for m in modules do
      let name := jstr m "name"
      key := key ++ "|" ++ jstr m "hash"
      match cache.get? key with
      | some (e, rep) =>
        env := e
        modReports := modReports ++ rep
      | none =>
        let path := jstr m "path"
        let (e1, strictErrs) ← elabOn env path (Name.mkStr `Defs name) strictOpts
        let (e2, defaultErrs) ←
          if strictErrs.isEmpty then pure (e1, #[])
          else elabOn env path (Name.mkStr `Defs name) baseOpts
        let rep := #[Json.mkObj [("module", name), ("strict_errors", toJson strictErrs),
          ("default_errors", toJson defaultErrs)]]
        let rep := if strictErrs.isEmpty then #[] else rep
        cache := cache.insert key (e2, rep)
        env := e2
        modReports := modReports ++ rep
    let stmt := jstr t "statement"
    let modName := Name.mkStr (Name.mkStr `Nodes tid) "Statement"
    let (_, defaultErrs) ← elabOn env stmt modName baseOpts
    let (_, strictErrs) ← elabOn env stmt modName strictOpts
    IO.println (Json.mkObj [("target", tid), ("default_errors", toJson defaultErrs),
      ("strict_errors", toJson strictErrs), ("modules", toJson modReports)]).compress
    (← IO.getStdout).flush
  return 0
