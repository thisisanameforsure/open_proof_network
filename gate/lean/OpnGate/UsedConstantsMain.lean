import OpnGate.Frontend
import OpnGate.UsedConstants

/-!
`opn-used-constants --file <Proof.lean> --module <Name> --decl <Name>`

Prints `{"ok": true, "decl": ..., "constants": [{"name", "module"}], "axioms": [...]}`.
-/
open Lean Elab OpnGate

unsafe def main (args : List String) : IO UInt32 := runMain do
  let (kv, _) := parseArgs args
  let some path := getArg kv "file" | fail "missing --file"
  let some modStr := getArg kv "module" | fail "missing --module"
  let some declStr := getArg kv "decl" | fail "missing --decl"
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
