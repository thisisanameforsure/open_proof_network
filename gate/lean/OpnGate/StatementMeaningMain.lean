import OpnGate.Frontend

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

Every constant the statement's type mentions comes from a module both headers import, so it is
the same declaration on both sides, with one exception this program checks: a constant the
statement's own file declares (a local `def` above the theorem). The artifact's file declares it
again, in the larger environment, and it too could have come out different. Each such constant
the type reaches (`locals`) must be the same declaration in the artifact's environment, type
and value, or it is named in `local_mismatch` and `matches` is false.
-/
open Lean OpnGate

namespace OpnGate

/-- The statement module's own constants that `start` reaches, through their types and values. -/
partial def localClosure (locals : Std.HashMap Name ConstantInfo) (start : Expr) : Array Name :=
  Id.run do
    let mut seen : NameSet := {}
    let mut out : Array Name := #[]
    let mut todo : List Name := start.getUsedConstants.toList
    while true do
      match todo with
      | [] => break
      | n :: rest =>
        todo := rest
        if seen.contains n then continue
        seen := seen.insert n
        let some info := locals[n]? | continue
        out := out.push n
        for c in info.getUsedConstantsAsSet.toList do
          todo := c :: todo
    return out.qsort (·.toString < ·.toString)

/-- Whether two declarations of one name are the same declaration: kind, universe parameters,
type and value, as terms. -/
def sameDeclaration (a b : ConstantInfo) : Bool :=
  a.levelParams == b.levelParams && a.type == b.type
    && a.value? (allowOpaque := true) == b.value? (allowOpaque := true)
    && a.isTheorem == b.isTheorem && a.isDefinition == b.isDefinition
    && a.isAxiom == b.isAxiom && a.isInductive == b.isInductive && a.isCtor == b.isCtor

end OpnGate

unsafe def main (args : List String) : IO UInt32 := runMain do
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

  let env ← importModules #[{ module := artMod.toName }] {} (loadExts := true)
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
