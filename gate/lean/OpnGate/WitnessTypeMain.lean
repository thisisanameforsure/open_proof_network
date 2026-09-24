import OpnGate.Frontend
import OpnGate.WitnessType

/-!
`opn-witness-type --statement <Statement.lean> --module <Name> --decl <Name>
                  [--witness <Witness.lean> --witness-module <Name>] [--proved <i,j,…>]`

Prints `{"ok": true, "expected": <type>, "witness": <type or null>, "defeq": <bool or null>,
"witness_axioms": [...]}`. The witness file is elaborated on top of the statement's environment
so both types live in one environment for the definitional-equality check (F01-R3).
-/
open Lean Meta Elab OpnGate

/-- `--proved 4,5`: the statement's binders the merged assembly proved (D-29 v3.22), from the
hole's `META.yaml`. Absent or empty is a hole with no record, whose expected type is today's. -/
def parseProved : Option String → Array Nat
  | none => #[]
  | some s => ((s.splitOn ",").filterMap fun p => p.trimAscii.toString.toNat?).toArray

/-- (v3.22) Prints `{"ok": true, "expected": …, …}` as before; with `--proved`, `expected` is the
narrowed type (`expectedWitnessTypeNarrowed`) and `defeq` is true of a witness of either it or
the full type. -/
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
  let proved := parseProved (getArg kv "proved")
  let (expected, _, _) ← (expectedWitnessTypeNarrowed info.type proved).toIO ctx coreState
  -- D-29 v3.22: a witness of the full type exhibits more than it must and is still a witness,
  -- so a hole with a record accepts either; without one the two are the same expression.
  let (full, _, _) ← (expectedWitnessType info.type).toIO ctx coreState
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
          <||> (pure !proved.isEmpty <&&>
            (withReducible (isDefEq full winfo.type) <||> isDefEq full winfo.type))
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
