import OpnGate.Frontend
import OpnGate.Close

/-!
`opn-close --file <assembly.lean> --module <Name> --decl <Name> --children <children.json>
          --out-olean <path>`

Joins a node's merged assembly with its children's proofs at the level of terms, has the kernel
check the result, and writes the node's `Proof` module to `--out-olean` (F28-T7, decisions v3.42).
Prints `{"ok": true, "decl", "holes": [{"hole", "child"}], "axioms", "olean"}`, or an error
document. `children.json` is an array of `{"node", "decl"}`. Runs only in the step-3 sandbox.
-/
open Lean OpnGate

def readChildren (path : String) : IO (Array Close.Child) := do
  let j ← IO.ofExcept (Json.parse (← IO.FS.readFile path))
  let arr ← IO.ofExcept j.getArr?
  arr.mapM fun c => do
    let node ← IO.ofExcept (c.getObjValAs? String "node")
    let decl ← IO.ofExcept (c.getObjValAs? String "decl")
    return { node, decl := decl.toName }

unsafe def main (args : List String) : IO UInt32 :=
  runMain args do
    let (kv, _) := parseArgs args
    let some file := getArg kv "file" | fail "missing --file"
    let some modStr := getArg kv "module" | fail "missing --module"
    let some declStr := getArg kv "decl" | fail "missing --decl"
    let some childrenPath := getArg kv "children" | fail "missing --children"
    let some out := getArg kv "out-olean" | fail "missing --out-olean"
    let children ← readChildren childrenPath
    printJson (← Close.run file modStr.toName declStr.toName children out)
    return 0
