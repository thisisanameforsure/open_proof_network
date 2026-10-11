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

/-- The environment `path`'s imports give, before any of its own commands are elaborated.

Imports happen once per process: a second `processHeader` in the same run returns an environment
without the parser extensions, so a file elaborated after another loses `∧`, `¬` and every other
notation (observed on Lean 4.33, not assumed). A metaprogram that needs two files therefore
imports once, here, and elaborates each file's commands on top of the result. -/
def headerEnv (path : System.FilePath) (moduleName : Name) : IO (Environment × MessageLog) := do
  let input ← IO.FS.readFile path
  let inputCtx := Parser.mkInputContext input path.toString
  let (stx, _, messages) ← Parser.parseHeader inputCtx
  processHeader stx {} messages inputCtx (mainModule := moduleName)

/-- The modules `path`'s header imports, in order. -/
def fileImports (path : System.FilePath) : IO (Array Name) := do
  let input ← IO.FS.readFile path
  let inputCtx := Parser.mkInputContext input path.toString
  let (stx, _, _) ← Parser.parseHeader inputCtx
  let header : HeaderSyntax := stx
  let mut out : Array Name := #[]
  for imp in header.imports (includeInit := false) do
    unless out.contains imp.module do out := out.push imp.module
  return out

/-- The environment the *union* of these files' imports gives.

A metaprogram that compares two or three files needs one environment they can all be elaborated
into, and no single file's header is necessarily a superset of the others': a variant's statement
imports its own `Context`, the root's imports the root's. So the union is synthesised as a header
of its own and imported once (see `headerEnv` for why once). -/
def unionHeaderEnv (paths : Array System.FilePath) (moduleName : Name)
    : IO (Environment × MessageLog) := do
  let mut names : Array Name := #[]
  for path in paths do
    for module in ← fileImports path do
      unless names.contains module do names := names.push module
  let text := String.join (names.toList.map fun n => s!"import {n}\n")
  let inputCtx := Parser.mkInputContext text "<opn-imports>"
  let (stx, _, messages) ← Parser.parseHeader inputCtx
  processHeader stx {} messages inputCtx (mainModule := moduleName)

/-- Elaborate `path` as module `moduleName`.

With `base? = none` the file's own header is processed (imports resolved via `LEAN_PATH`).
With `base? = some env` the file's commands are elaborated on top of `env` instead, and its
header may import only modules `env` already imported — so two files can share one environment
(the statement and its witness). `opts` are the options the commands elaborate under; the
default is Lean's (F02-T9's `auto-implicit` passes `autoImplicit := false`). -/
def elabFile (path : System.FilePath) (moduleName : Name) (base? : Option Environment := none)
    (opts : Options := {}) : IO (Environment × MessageLog) := do
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
  let s ← IO.processCommands inputCtx parserState (Command.mkState env messages opts)
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

/-- The tag a metaprogram's verdict line carries when its caller passed a nonce (F02-T11):
`@opn-verdict <nonce> <json>`. The Python side accepts exactly one line so tagged. -/
def verdictTag : String := "@opn-verdict"

/-- The caller's per-call nonce: the first line of stdin, when `--nonce stdin` is among the
arguments. Read before anything else happens, so nothing the program goes on to import or
elaborate can read it from stdin. -/
def readNonce (args : List String) : IO (Option String) := do
  unless getArg (parseArgs args).1 "nonce" == some "stdin" do return none
  let line ← (← IO.getStdin).getLine
  let nonce := line.trimAscii.copy
  if nonce.isEmpty then
    throw <| IO.userError "--nonce stdin was given, but stdin carried no nonce"
  return some nonce

/-- Run `body` with stdin, stdout and stderr captured, then print the line it printed last as the
verdict, tagged with `nonce` (F02-T11). A sentinel carrying the nonce is printed into the capture
after `body` returns, and the verdict is taken only when that sentinel is the last line captured:
code that ran inside `body` and swapped stdout to the real one, or printed after `body`'s own
verdict, leaves no tagged verdict at all. Everything else captured goes to stderr. -/
def emitTagged (nonce : String) (body : IO UInt32) : IO UInt32 := do
  let sentinel := s!"{verdictTag} {nonce} end"
  let (out, code) ← IO.FS.withIsolatedStreams (isolateStderr := false) do
    let code ← body
    IO.println sentinel
    return code
  let lines := (out.splitOn "\n").filter (fun l => !l.isEmpty)
  match lines.reverse with
  | last :: verdict :: _ =>
    if last == sentinel && !(verdict.startsWith verdictTag) then
      for l in lines.dropLast.dropLast do IO.eprintln l
      IO.println s!"{verdictTag} {nonce} {verdict}"
      return code
    for l in lines do IO.eprintln l
    return 1
  | _ =>
    for l in lines do IO.eprintln l
    return 1

/-- Run a metaprogram body with the search path initialised from the toolchain and `LEAN_PATH`.

`initializers`: whether imported modules' `initialize` blocks run. A program that elaborates a
file must (importing with extensions requires it, and Mathlib's attributes are registered that
way), and so contributor code in a module such a file imports runs in it. A program that only
reads compiled modules (`opn-statement-meaning`, `opn-axioms`) passes `false` and imports with
`loadExts := false`: nothing of the imported modules is executed there (F02-T11).

With `--nonce stdin` the verdict is printed tagged (`emitTagged`); without it, as before. -/
unsafe def runMain (args : List String) (body : IO UInt32) (initializers := true) :
    IO UInt32 := do
  let nonce? ← readNonce args
  if initializers then enableInitializersExecution
  initSearchPath (← findSysroot)
  let guarded : IO UInt32 := do
    try body
    catch e => fail (toString e)
  match nonce? with
  | none => guarded
  | some nonce => emitTagged nonce guarded

end OpnGate
