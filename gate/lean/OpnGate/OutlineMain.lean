import OpnGate.Frontend
import OpnGate.Outline

/-!
`opn-outline --file <Proof.lean> --module <Name> --decl <Name>
             --automation omega,simp,... --doc-modules Init,Std,Lean,Mathlib,...
             [--printer roundtrip|plain] [--nonce stdin]`   (F19-R1 to R4)

Prints `{"ok": true, "decl", "steps": [...], "constants": {name: {"module", "doc", "tags"}}}`:
the step tree of the declaration's proof (see `OpnGate.Outline`), and every constant a step
names, with its module and, for a module under a `--doc-modules` prefix, its docstring and its
Stacks or Kerodon tags. Ids, caps and the graph/defs/library split are the Python wrapper's
(`opn_gate.outline`). `--printer plain` exists for the lean tier alone (F19-AC3: a printer that
drops ascriptions); the gate never passes it.

The artifact is elaborated here, its info trees kept: only ever inside the step-3 sandbox.
-/
open Lean OpnGate

def splitList (s : String) : Array String :=
  ((s.splitOn ",").map (·.trimAscii.copy) |>.filter (!·.isEmpty)).toArray

unsafe def main (args : List String) : IO UInt32 :=
  runMain args do
    let (kv, _) := parseArgs args
    let some file := getArg kv "file" | fail "missing --file"
    let some modStr := getArg kv "module" | fail "missing --module"
    let some declStr := getArg kv "decl" | fail "missing --decl"
    let automation := splitList ((getArg kv "automation").getD "")
    let docPrefixes := (splitList ((getArg kv "doc-modules").getD "")).map (·.toName)
    let roundTrip ← match (getArg kv "printer").getD "roundtrip" with
      | "roundtrip" => pure true
      | "plain" => pure false
      | other => throw <| IO.userError s!"unknown --printer {other}"
    match ← Outline.outline file modStr.toName declStr.toName automation docPrefixes roundTrip with
    | .error e => fail e
    | .ok doc =>
      printJson doc
      return 0
