import OpnGate.Frontend
import OpnGate.ArtifactType

/-!
`opn-relation-type --variant <Statement.lean> --variant-module <Name> --variant-decl <Name>
                  --root <Statement.lean> --root-module <Name> --root-decl <Name>
                  --label resolves|partial|related
                  [--relation <Relation.lean> --relation-module <Name> --relation-decl <Name>]`

Prints `{"ok": true, "label", "expected", "declared", "matches", "axioms"}` (D-30; F08-R4).

A `related` label claims no implication, so it needs no file: the answer is `matches: true` with
a null expected type. Above `related` the label is a claim, and the claim is this program's whole
subject — whether `Relation.lean` proves the implication the label asserts, in the direction it
asserts it.

The three files are elaborated from one imported environment, for the reason
`OpnGate.Frontend.headerEnv` documents: imports happen once per process, and the root and the
variant declare different names but cannot be assumed to.
-/
open Lean Meta Elab OpnGate

unsafe def main (args : List String) : IO UInt32 := runMain do
  let (kv, _) := parseArgs args
  let some variantPath := getArg kv "variant" | fail "missing --variant"
  let some variantMod := getArg kv "variant-module" | fail "missing --variant-module"
  let some variantDecl := getArg kv "variant-decl" | fail "missing --variant-decl"
  let some rootPath := getArg kv "root" | fail "missing --root"
  let some rootMod := getArg kv "root-module" | fail "missing --root-module"
  let some rootDecl := getArg kv "root-decl" | fail "missing --root-decl"
  let some labelStr := getArg kv "label" | fail "missing --label"
  let some label := RelationLabel.ofString? labelStr
    | fail s!"unknown relation label {labelStr}"

  let relPath? := getArg kv "relation"
  let headerPaths : Array System.FilePath :=
    (#[variantPath, rootPath] ++ (relPath?.toArray)).map System.FilePath.mk
  let (base, baseLog) ← unionHeaderEnv headerPaths variantMod.toName
  if let some code ← failIfErrors "imports" baseLog then return code

  let (variantEnv, variantLog) ← elabFile variantPath variantMod.toName (some base)
  if let some code ← failIfErrors "variant statement" variantLog then return code
  let some variantInfo := variantEnv.find? variantDecl.toName
    | fail s!"declaration {variantDecl} not found in {variantPath}"

  -- F08-T15: when the root is one of the variant's declared deps, the variant's own Context,
  -- which its statement imports, already restates the root's theorem, and elaborating the root's
  -- file on top of it is "already declared". The declaration in the imported environment is the
  -- one to relate to: admission's `context` check, which runs before this one, has verified that
  -- the Context carries each declared dep's signature (F01-R6). A probe that imports the thing
  -- it is compared against must not declare it again.
  let mut rootInfo? := base.find? rootDecl.toName
  if rootInfo?.isNone then
    let (rootEnv, rootLog) ← elabFile rootPath rootMod.toName (some base)
    if let some code ← failIfErrors "root statement" rootLog then return code
    rootInfo? := rootEnv.find? rootDecl.toName
  let some rootInfo := rootInfo?
    | fail s!"declaration {rootDecl} not found in {rootPath}"

  if label == RelationLabel.related then
    printJson <| Json.mkObj [
      ("ok", Json.bool true), ("label", Json.str label.toString),
      ("expected", Json.null), ("declared", Json.null),
      ("matches", Json.bool true), ("axioms", Json.arr #[])]
    return 0

  let some relPath := relPath?
    | fail s!"a {label.toString} variant needs --relation (D-30: the label is a claim)"
  let some relMod := getArg kv "relation-module" | fail "missing --relation-module"
  let some relDecl := getArg kv "relation-decl" | fail "missing --relation-decl"
  let (relEnv, relLog) ← elabFile relPath relMod.toName (some base)
  if let some code ← failIfErrors "relation" relLog then return code
  let some relInfo := relEnv.find? relDecl.toName
    | fail s!"{relPath} does not declare {relDecl}"

  let ctx : Core.Context := { fileName := relPath, fileMap := default }
  let state : Core.State := { env := relEnv }
  let ((expectedStr, declaredStr, typeMatches), _, _) ← (do
      let some expected ← expectedRelationType label variantInfo.type rootInfo.type
        | throwError "a labeled variant has an expected relation type"
      let ok ← withReducible (isDefEq expected relInfo.type) <||> isDefEq expected relInfo.type
      return (toString (← ppExpr expected), toString (← ppExpr relInfo.type), ok)
      : MetaM (String × String × Bool)).toIO ctx state
  let (axioms, _) ← (collectAxioms relDecl.toName : CoreM (Array Name)).toIO ctx state

  printJson <| Json.mkObj [
    ("ok", Json.bool true),
    ("label", Json.str label.toString),
    ("decl", Json.str relDecl),
    ("expected", Json.str expectedStr),
    ("declared", Json.str declaredStr),
    ("matches", Json.bool typeMatches),
    ("axioms", toJson (axioms.map toString))]
  return 0
