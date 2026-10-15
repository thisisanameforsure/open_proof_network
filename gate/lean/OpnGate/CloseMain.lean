import OpnGate.Frontend
import OpnGate.Close

/-!
`opn-close --file <assembly.lean> --module <Name> --decl <Name> --children <children.json>`

Prints `{"ok": true, "sites": [...], "composed": "<the closing proof>"}`, or `"ok": false` with
the sites and the reason (F28-R4). `children.json` is an array of `{"node", "decl"}`: the route's
hole nodes in the route's order, each with its theorem's name. Runs only in the step-3 sandbox.
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
    let children ← readChildren childrenPath
    printJson (← Close.compose file modStr.toName declStr.toName children)
    return 0
