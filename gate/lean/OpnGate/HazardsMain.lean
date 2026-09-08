import OpnGate.Frontend
import OpnGate.Hazards
import OpnGate.Hazards.NatSub
import OpnGate.Hazards.DivZero
import OpnGate.Hazards.JunkValue
import OpnGate.Hazards.IntTrunc
import OpnGate.Hazards.UnusedBinder
import OpnGate.Hazards.OffByOneRange

/-!
`opn-hazards --statement <Statement.lean> --module <Name> --decl <Name> --checkers a,b,c`
`opn-hazards --list`

Runs exactly the named checkers over the theorem's type (F02-R1, R3) and prints
`{"ok": true, "decl": ..., "checkers": [...], "findings": [{checker, location, message}],
"capped": bool}`. An unknown checker id is an error before anything is elaborated. `--list`
prints `{"ok": true, "checkers": [{id, describe}]}` so the Python side can cross-check its
registry against this one.
-/
open Lean Meta Elab OpnGate OpnGate.Hazards

/-- Every checker this gate version ships, in id order. -/
def registry : Array Checker :=
  #[divZero, intTrunc, junkValue, natSub, offByOneRange, unusedBinder]

unsafe def main (args : List String) : IO UInt32 := runMain do
  if args == ["--list"] then
    printJson <| Json.mkObj [
      ("ok", Json.bool true),
      ("checkers", toJson (registry.map fun c =>
        Json.mkObj [("id", Json.str c.id), ("describe", Json.str c.describe)]))]
    return 0
  let (kv, _) := parseArgs args
  let some stmtPath := getArg kv "statement" | fail "missing --statement"
  let some modStr := getArg kv "module" | fail "missing --module"
  let some declStr := getArg kv "decl" | fail "missing --decl"
  let ids := ((getArg kv "checkers").getD "").splitOn "," |>.filter (· ≠ "")
  let mut selected : Array Checker := #[]
  for id in ids do
    match registry.find? (·.id == id) with
    | some c => selected := selected.push c
    | none =>
      return ← fail s!"unknown checker id {id}"
        [("known", toJson (registry.map (·.id)))]
  let (env, log) ← elabFile stmtPath modStr.toName
  if let some code ← failIfErrors "statement" log then return code
  let declName := declStr.toName
  let some info := env.find? declName | fail s!"declaration {declStr} not found in {stmtPath}"
  let ctx : Core.Context := { fileName := stmtPath, fileMap := default }
  let ((findings, capped), _, _) ← (run selected info.type).toIO ctx { env }
  printJson <| Json.mkObj [
    ("ok", Json.bool true), ("decl", Json.str declStr),
    ("checkers", toJson (selected.map (·.id))),
    ("findings", toJson findings), ("capped", Json.bool capped)]
  return 0
