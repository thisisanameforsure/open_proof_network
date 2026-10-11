import OpnGate.Frontend
import OpnGate.WitnessType
import OpnGate.Compiled

/-!
`opn-witness-type --module <Statement module> --decl <Name>
                  [--witness-olean <Witness.olean>] [--proved <i,j,…>]`

Prints `{"ok": true, "expected": <type>, "witness": <type or null>, "defeq": <bool or null>,
"witness_axioms": [...]}` (F01-R3).

**Nothing of the witness runs here (F02-T12).** The statement's environment is imported from its
compiled module, which the gate built in the judging directory from the node's own files (with
the target's definitions and Mathlib: nothing a contributor's process produced). The witness is
never elaborated in this process: the gate compiled it in a call of its own, as a module that
imports the statement's (`import <Statement module>` in place of its own header, whose imports
must be the statement's), and this program reads that olean as data and adds each of its
constants through the kernel (`replayInto`). So both types live in one environment, with every
notation and instance the statement's imports give, exactly as when the witness was elaborated on
top of the statement here before T12; and an `#eval`, an `initialize` or a macro in the witness
ran, if at all, in the compile, whose output is not the verdict.
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
unsafe def main (args : List String) : IO UInt32 := runMain args do
  let (kv, _) := parseArgs args
  if (getArg kv "witness").isSome || (getArg kv "statement").isSome then
    return ← fail "opn-witness-type reads compiled modules only: --module and --witness-olean (F02-T12)"
  let some modStr := getArg kv "module" | fail "missing --module"
  let some declStr := getArg kv "decl" | fail "missing --decl"
  let declName := declStr.toName
  -- The statement's module and its imports are the graph's record, built by the gate: imported
  -- with their extensions, which is what elaborating the statement here used to give.
  let env ← importModules #[{ module := modStr.toName }] {} (loadExts := true)
  let some idx := env.getModuleIdxFor? declName
    | fail s!"declaration {declStr} not found in {modStr}"
  unless env.header.moduleNames[idx.toNat]! == modStr.toName do
    return ← fail s!"{declStr} is declared by {env.header.moduleNames[idx.toNat]!}, not {modStr}"
  let some info := env.find? declName | fail s!"declaration {declStr} not found in {modStr}"
  let ctx : Core.Context := { fileName := modStr, fileMap := default }
  let coreState : Core.State := { env }
  let proved := parseProved (getArg kv "proved")
  let (expected, _, _) ← (expectedWitnessTypeNarrowed info.type proved).toIO ctx coreState
  -- D-29 v3.22: a witness of the full type exhibits more than it must and is still a witness,
  -- so a hole with a record accepts either; without one the two are the same expression.
  let (full, _, _) ← (expectedWitnessType info.type).toIO ctx coreState
  let (expectedStr, _, _) ← (do return toString (← ppExpr expected) : MetaM String).toIO ctx coreState
  match getArg kv "witness-olean" with
  | some wPath =>
    let (consts, _) ← readOlean wPath
    let witnessName := `witness
    unless consts.any (·.name == witnessName) do
      return ← fail "Witness.lean must declare exactly one declaration named `witness`"
          [("expected", Json.str expectedStr)]
    -- F02-T12: added through the kernel, never executed.
    let replayed ← (try pure (Except.ok (← replayInto env consts))
      catch e => pure (Except.error (toString e)) : IO (Except String Environment))
    let env2 ← match replayed with
      | .ok env2 => pure env2
      | .error e =>
        return ← fail s!"witness does not elaborate: {e}" [("expected", Json.str expectedStr)]
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
  | none =>
    printJson <| Json.mkObj [
      ("ok", Json.bool true), ("expected", Json.str expectedStr),
      ("witness", Json.null), ("defeq", Json.null), ("witness_axioms", Json.arr #[])]
    return 0
