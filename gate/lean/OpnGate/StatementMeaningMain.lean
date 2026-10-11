import OpnGate.Frontend
import OpnGate.Compiled

/-!
`opn-statement-meaning --statement-olean <Statement.olean> --decl <Name>
                       --artifact-module <Name> --artifact-decl <Name>`

Prints `{"ok": true, "decl", "expected", "declared", "identical", "matches", "locals",
"local_mismatch"}` (F08-R16; D-3, D-4, proposed v3.25).

**What it answers.** An artifact that declares uses (extra `import Defs.*` or
`import Nodes.«id».Proof` lines) is elaborated in a larger environment than its statement was.
The artifact file repeats the statement's text, and the same text can elaborate to a different
term there: an added instance, a notation, an `open`ed name that now resolves elsewhere. So the
type the artifact proved is compared with the type the statement has *in the statement's own
environment*, and nothing is elaborated here at all:

* the statement's type is read from the olean the gate compiled from `Statement.lean` under the
  statement's own header (`readModuleData`: the file's constants, with no import of it, so the
  artifact's module, which declares the same name, can be the environment);
* the artifact's type is the declaration in the environment of the artifact's compiled module;
* `matches` is the kernel's word that the two are definitionally equal in that environment
  (`identical` when they are the same term outright).

**What runs here** (F02-T11): nothing of the artifact's. Its module is imported with
initializers off and without its extension data (`runMain … (initializers := false)`,
`loadExts := false`), so an `initialize` block in it cannot print a verdict of its own, and the
verdict is printed tagged with the caller's nonce. Printing a type may then show fewer notations
than an elaborating program would; it is for the reader of a refusal only.

Every constant the statement's type mentions comes from a module both headers import, so it is
the same declaration on both sides, with one exception this program checks: a constant the
statement's own file declares (a local `def` above the theorem). The artifact's file declares it
again, in the larger environment, and it too could have come out different. Each such constant
the type reaches (`locals`) must be the same declaration in the artifact's environment, type
and value, or it is named in `local_mismatch` and `matches` is false.
-/
open Lean OpnGate


unsafe def main (args : List String) : IO UInt32 := runMain args (initializers := false) do
  let (kv, _) := parseArgs args
  let some oleanPath := getArg kv "statement-olean" | fail "missing --statement-olean"
  let some stmtDecl := getArg kv "decl" | fail "missing --decl"
  let some artMod := getArg kv "artifact-module" | fail "missing --artifact-module"
  let some artDecl := getArg kv "artifact-decl" | fail "missing --artifact-decl"

  let (data, _) ← readModuleData oleanPath
  let mut locals : Std.HashMap Name ConstantInfo := {}
  for info in data.constants do
    locals := locals.insert info.name info
  let some stmtInfo := locals[stmtDecl.toName]?
    | fail s!"declaration {stmtDecl} not found in {oleanPath}"

  -- F02-T11: the artifact's environment is read, never run: initializers are off and no
  -- extension data is loaded, so an `initialize` block in the artifact (or in anything it
  -- imports) does not execute here. The constants are all the kernel comparison needs.
  let env ← importModules #[{ module := artMod.toName }] {} (loadExts := false)
  let some artInfo := env.find? artDecl.toName
    | fail s!"module {artMod} does not declare {artDecl}"

  let reached := localClosure locals stmtInfo.type
  let mut mismatch : Array String := #[]
  for name in reached do
    let some own := locals[name]? | continue
    match env.find? name with
    | some theirs => unless sameDeclaration own theirs do mismatch := mismatch.push name.toString
    | none => mismatch := mismatch.push name.toString

  let identical := stmtInfo.type == artInfo.type && stmtInfo.levelParams == artInfo.levelParams
  let defeq := identical || (stmtInfo.levelParams == artInfo.levelParams
    && Kernel.isDefEqGuarded env {} stmtInfo.type artInfo.type)
  -- Printing is for the reader of a refusal. Two types that differ only in an instance print
  -- alike by default, so a mismatch is shown with every argument explicit; a type that names a
  -- constant this environment lacks cannot be pretty-printed and is shown raw, never as a pass.
  let opts : Options := if identical then {} else ({} : Options).setBool `pp.explicit true
  let ctx : Core.Context :=
    { fileName := "<opn-statement-meaning>", fileMap := default, options := opts }
  let state : Core.State := { env }
  let show_ (e : Expr) : IO String := do
    try
      let (fmt, _) ← (Meta.ppExpr e).run'.toIO ctx state
      return toString fmt
    catch _ => return toString e
  printJson <| Json.mkObj [
    ("ok", Json.bool true),
    ("decl", Json.str stmtDecl),
    ("expected", Json.str (← show_ stmtInfo.type)),
    ("declared", Json.str (← show_ artInfo.type)),
    ("identical", Json.bool identical),
    ("matches", Json.bool (defeq && mismatch.isEmpty)),
    ("locals", toJson (reached.map toString)),
    ("local_mismatch", toJson mismatch)]
  return 0
