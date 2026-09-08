import Lean

/-!
Step 8's dependency footprint (F01-R4): every constant a declaration depends on, transitively
through declarations introduced in the same file (those with no module of their own), each with
the module it came from — `null` for the submission itself.
-/
open Lean

namespace OpnGate

structure UsedConstant where
  name : String
  module : Option String
deriving ToJson

/-- Transitive closure over same-file declarations; imported constants are leaves. -/
partial def usedConstants (env : Environment) (root : Name) : Array UsedConstant := Id.run do
  let mut seen : NameSet := {}
  let mut todo : List Name := [root]
  let mut out : Array UsedConstant := #[]
  while true do
    match todo with
    | [] => break
    | n :: rest =>
      todo := rest
      if seen.contains n then continue
      seen := seen.insert n
      let some info := env.find? n | continue
      let module? := (env.getModuleIdxFor? n).map fun idx => env.header.moduleNames[idx.toNat]!
      if n != root then
        out := out.push { name := n.toString, module := module?.map toString }
      -- Recurse only through declarations of this file (no module index), including the root.
      if module?.isNone then
        for c in info.getUsedConstantsAsSet.toList do
          todo := c :: todo
  return out.qsort (·.name < ·.name)

end OpnGate
