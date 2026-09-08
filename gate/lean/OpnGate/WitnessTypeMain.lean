import OpnGate.Frontend
import OpnGate.WitnessType

/-!
`opn-witness-type --statement <Statement.lean> --module <Name> --decl <Name>
                  [--witness <Witness.lean> --witness-module <Name>]`

Prints `{"ok": true, "expected": <type>, "witness": <type or null>, "defeq": <bool or null>,
"witness_axioms": [...]}`. The witness file is elaborated on top of the statement's environment
so both types live in one environment for the definitional-equality check (F01-R3).
-/
open Lean Meta Elab OpnGate

unsafe def main (args : List String) : IO UInt32 := runMain do
  let (kv, _) := parseArgs args
  let some stmtPath := getArg kv "statement" | fail "missing --statement"
  let some modStr := getArg kv "module" | fail "missing --module"
  let some declStr := getArg kv "decl" | fail "missing --decl"
  let moduleName := modStr.toName
  let declName := declStr.toName
  let (env, log) ← elabFile stmtPath moduleName
  if let some code ← failIfErrors "statement" log then return code
  let some info := env.find? declName | fail s!"declaration {declStr} not found in {stmtPath}"
  let ctx : Core.Context := { fileName := stmtPath, fileMap := default }
  let coreState : Core.State := { env }
  let (expected, _, _) ← (expectedWitnessType info.type).toIO ctx coreState
  let (expectedStr, _, _) ← (do return toString (← ppExpr expected) : MetaM String).toIO ctx coreState
  match getArg kv "witness", getArg kv "witness-module" with
  | some wPath, some wMod =>
    let (env2, log2) ← elabFile wPath wMod.toName (some env)
    if let some code ← failIfErrors "witness" log2 then return code
    let witnessName := `witness
    let some winfo := env2.find? witnessName
      | return ← fail "Witness.lean must declare exactly one declaration named `witness`"
          [("expected", Json.str expectedStr)]
    let coreState2 : Core.State := { env := env2 }
    let ((witnessStr, defeq, axioms), _, _) ← (do
        let w ← ppExpr winfo.type
        let ok ← withReducible (isDefEq expected winfo.type) <||> isDefEq expected winfo.type
        let ax ← collectAxioms witnessName
        return (toString w, ok, ax) : MetaM (String × Bool × Array Name)).toIO ctx coreState2
    printJson <| Json.mkObj [
      ("ok", Json.bool true), ("expected", Json.str expectedStr),
      ("witness", Json.str witnessStr), ("defeq", Json.bool defeq),
      ("witness_axioms", toJson (axioms.map toString))]
    return 0
  | _, _ =>
    printJson <| Json.mkObj [
      ("ok", Json.bool true), ("expected", Json.str expectedStr),
      ("witness", Json.null), ("defeq", Json.null), ("witness_axioms", Json.arr #[])]
    return 0
