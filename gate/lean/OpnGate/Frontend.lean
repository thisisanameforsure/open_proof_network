import Lean

/-!
Shared plumbing for the gate's metaprograms: elaborate a file into an environment, report
messages as data, and print JSON results in the one shape the Python side parses (F01-R1, R9).
-/
open Lean Elab

namespace OpnGate

/-- One elaboration message, as plain data. -/
structure Msg where
  severity : String
  line : Nat
  column : Nat
  text : String
deriving ToJson

def Msg.ofMessage (m : Message) : IO Msg := do
  let text ← m.data.toString
  return {
    severity := match m.severity with
      | .error => "error" | .warning => "warning" | .information => "info"
    line := m.pos.line
    column := m.pos.column
    text
  }

def messagesToArray (log : MessageLog) : IO (Array Msg) := do
  let mut out := #[]
  for m in log.toList do
    out := out.push (← Msg.ofMessage m)
  return out

/-- Elaborate `path` as module `moduleName`.

With `base? = none` the file's own header is processed (imports resolved via `LEAN_PATH`).
With `base? = some env` the file's commands are elaborated on top of `env` instead, and its
header may import only modules `env` already imported — so two files can share one environment
(the statement and its witness). -/
def elabFile (path : System.FilePath) (moduleName : Name) (base? : Option Environment := none)
    : IO (Environment × MessageLog) := do
  let input ← IO.FS.readFile path
  let inputCtx := Parser.mkInputContext input path.toString
  let (stx, parserState, messages) ← Parser.parseHeader inputCtx
  let header : HeaderSyntax := stx
  let (env, messages) ← match base? with
    | none => processHeader header {} messages inputCtx (mainModule := moduleName)
    | some env =>
      let imported := env.allImportedModuleNames
      for imp in header.imports (includeInit := false) do
        unless imported.contains imp.module do
          throw <| IO.userError s!"{path}: import {imp.module} is not among the statement's imports"
      pure (env.setMainModule moduleName, messages)
  let s ← IO.processCommands inputCtx parserState (Command.mkState env messages {})
  return (s.commandState.env, s.commandState.messages)

def printJson (j : Json) : IO Unit := do
  IO.println j.compress

/-- Print `{"ok": false, "error": ..., ...}` and exit 1 (F01-R1). -/
def fail (error : String) (extra : List (String × Json) := []) : IO UInt32 := do
  printJson <| Json.mkObj (("ok", Json.bool false) :: ("error", Json.str error) :: extra)
  return 1

/-- Fail with the elaboration messages when the log has errors. -/
def failIfErrors (what : String) (log : MessageLog) : IO (Option UInt32) := do
  if log.hasErrors then
    let msgs ← messagesToArray log
    return some (← fail s!"{what} does not elaborate" [("messages", toJson msgs)])
  return none

/-- Parse `--key value` pairs and bare positionals. -/
partial def parseArgs (args : List String) : List (String × String) × List String :=
  go args [] []
where
  go (args : List String) (kv : List (String × String)) (pos : List String) :
      List (String × String) × List String :=
    match args with
    | [] => (kv.reverse, pos.reverse)
    | k :: v :: rest =>
      if k.startsWith "--" then go rest (((k.drop 2).toString, v) :: kv) pos
      else go (v :: rest) kv (k :: pos)
    | [k] => (kv.reverse, (k :: pos).reverse)

def getArg (kv : List (String × String)) (key : String) : Option String :=
  (kv.find? (·.1 == key)).map (·.2)

/-- Run a metaprogram body with the search path initialised from the toolchain and `LEAN_PATH`.
`unsafe` because importing modules with their extensions requires enabling initializers. -/
unsafe def runMain (body : IO UInt32) : IO UInt32 := do
  enableInitializersExecution
  initSearchPath (← findSysroot)
  try body
  catch e => fail (toString e)

end OpnGate
