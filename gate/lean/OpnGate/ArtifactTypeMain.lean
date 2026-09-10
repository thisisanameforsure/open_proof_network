import OpnGate.Frontend
import OpnGate.ArtifactType
import OpnGate.Holes

/-!
`opn-artifact-type --statement <Statement.lean> --module <Name> --decl <Name>
                  --artifact <file.lean> --artifact-module <Name> --artifact-decl <Name>
                  --kind proof|counterexample|vacuity|partial|reduction`

Prints `{"ok": true, "kind", "expected", "declared", "matches", "axioms", "holes", "unnamed",
"body_is_hole"}` (F07-R4, R5).

The two files are elaborated independently and compared in the artifact's environment. They
cannot share one environment the way a statement and its witness do (F01-R3), because a partial
proof declares the statement's own name: putting both in one environment is a duplicate
declaration, not a comparison. Comparing across the two is sound here because the statement's
type mentions only constants from the imports both files share — and if it ever mentions one the
artifact does not import, the comparison fails, which is the right answer.
-/
open Lean Meta Elab OpnGate

unsafe def main (args : List String) : IO UInt32 := runMain do
  let (kv, _) := parseArgs args
  let some stmtPath := getArg kv "statement" | fail "missing --statement"
  let some stmtMod := getArg kv "module" | fail "missing --module"
  let some stmtDecl := getArg kv "decl" | fail "missing --decl"
  let some artPath := getArg kv "artifact" | fail "missing --artifact"
  let some artMod := getArg kv "artifact-module" | fail "missing --artifact-module"
  let some artDecl := getArg kv "artifact-decl" | fail "missing --artifact-decl"
  let some kindStr := getArg kv "kind" | fail "missing --kind"
  let some kind := ArtifactKind.ofString? kindStr
    | fail s!"unknown artifact kind {kindStr}"

  -- Import once, then elaborate each file's commands on its own copy of that environment.
  let (base, baseLog) ← unionHeaderEnv #[stmtPath, artPath] stmtMod.toName
  if let some code ← failIfErrors "imports" baseLog then return code

  let (stmtEnv, stmtLog) ← elabFile stmtPath stmtMod.toName (some base)
  if let some code ← failIfErrors "statement" stmtLog then return code
  let some stmtInfo := stmtEnv.find? stmtDecl.toName
    | fail s!"declaration {stmtDecl} not found in {stmtPath}"

  let (artEnv, artLog) ← elabFile artPath artMod.toName (some base)
  if let some code ← failIfErrors "artifact" artLog then return code
  let some artInfo := artEnv.find? artDecl.toName
    | fail s!"{artPath} does not declare {artDecl}"

  let ctx : Core.Context := { fileName := artPath, fileMap := default }
  let state : Core.State := { env := artEnv }
  let ((expectedStr, declaredStr, typeMatches, holes), _, _) ← (do
      let expected ← expectedArtifactType kind stmtInfo.type
      let ok ← withReducible (isDefEq expected artInfo.type) <||> isDefEq expected artInfo.type
      -- `allowOpaque := true`: a theorem's proof term is opaque for reduction, and this is the
      -- one place that wants to look at it rather than use it.
      let holes ← match artInfo.value? (allowOpaque := true) with
        | some value => holeReport stmtInfo.type value
        | none => pure { holes := #[], unnamed := 0, body_is_hole := false }
      return (toString (← ppExpr expected), toString (← ppExpr artInfo.type), ok, holes)
      : MetaM (String × String × Bool × HoleReport)).toIO ctx state
  let (axioms, _) ← (collectAxioms artDecl.toName : CoreM (Array Name)).toIO ctx state

  printJson <| Json.mkObj [
    ("ok", Json.bool true),
    ("kind", Json.str kind.toString),
    ("decl", Json.str artDecl),
    ("expected", Json.str expectedStr),
    ("declared", Json.str declaredStr),
    ("matches", Json.bool typeMatches),
    ("axioms", toJson (axioms.map toString)),
    ("holes", toJson holes.holes),
    ("unnamed", Json.num holes.unnamed),
    ("body_is_hole", Json.bool holes.body_is_hole)]
  return 0
