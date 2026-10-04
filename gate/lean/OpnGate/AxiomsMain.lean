import OpnGate.Frontend
import OpnGate.Compiled

/-!
`opn-axioms --module <Name> --decl <Name>`

Prints `{"ok": true, "decl": ..., "module": ..., "axioms": [...]}` (D-4 step 5; F02-T11).

**Why not `#print axioms`.** Step 5 used to run `lean` on a two-line probe file importing the
artifact's module. The `lean` frontend enables initializers, so an `initialize` block in the
artifact (step 2 accepts a command after a proof's body) ran in the probe and could print an
axioms line of its own; and `#print axioms` (`collectAxioms`, Lean 4.33) takes an imported
declaration's axioms from data the imported module's olean carries, computed when that module
was compiled, rather than from its body.

So this program imports the module with initializers off and without extension data, nothing of
it is executed, and the axioms are collected here by walking the declaration's constants (types,
values, an inductive's constructors) through the environment's constant table: the declarations
the kernel replay re-checked, not a summary stored beside them. `decl` must be declared by
`module` itself.
-/
open Lean OpnGate


unsafe def main (args : List String) : IO UInt32 := runMain args (initializers := false) do
  let (kv, _) := parseArgs args
  let some modStr := getArg kv "module" | fail "missing --module"
  let some declStr := getArg kv "decl" | fail "missing --decl"
  let declName := declStr.toName
  let env ← importModules #[{ module := modStr.toName }] {} (loadExts := false)
  let some idx := env.getModuleIdxFor? declName
    | fail s!"module {modStr} does not declare {declStr}"
  unless env.header.moduleNames[idx.toNat]! == modStr.toName do
    return ← fail s!"{declStr} is declared by {env.header.moduleNames[idx.toNat]!}, not {modStr}"
  match axiomsOf env declName with
  | .error e => fail e
  | .ok axioms =>
    printJson <| Json.mkObj [
      ("ok", Json.bool true), ("decl", Json.str declStr), ("module", Json.str modStr),
      ("axioms", toJson axioms)]
    return 0
