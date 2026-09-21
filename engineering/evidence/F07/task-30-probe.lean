import Lean
open Lean Meta Elab Term

def shape : Prop := ∀ b : Nat, 0 < b → ∃ N k : Nat, ∃ m : Nat, ((m : Int)) * 2 ≤ (N : Int) + k

def tryOpts (label : String) (f : Options → Options) : MetaM Unit := do
  let info ← getConstInfo ``shape
  let e := info.value!
  let s ← withOptions f do return toString (← ppExpr e)
  -- round trip: parse, elaborate as a type, compare
  let env ← getEnv
  let ok ← try
      match Parser.runParserCategory env `term s with
      | .error err => pure s!"PARSE ERROR {err}"
      | .ok stx =>
        let t ← (Term.elabType stx).run'
        let t ← instantiateMVars t
        if t.hasMVar then pure "ELABORATED WITH METAVARIABLES"
        else pure (if (← isDefEq t e) then "round-trips" else "DIFFERENT TYPE")
    catch ex => pure s!"ELAB ERROR {← ex.toMessageData.toString}"
  IO.println s!"[{label}] {ok}\n    {s}"

#eval tryOpts "gate today: coercions.types + numericTypes" fun o => (o.setBool `pp.coercions.types true).setBool `pp.numericTypes true
#eval tryOpts "+ pp.funBinderTypes" fun o => ((o.setBool `pp.coercions.types true).setBool `pp.numericTypes true).setBool `pp.funBinderTypes true
#eval tryOpts "+ pp.binderTypes (explicit)" fun o => ((o.setBool `pp.coercions.types true).setBool `pp.numericTypes true).setBool `pp.binderTypes true
#eval tryOpts "+ funBinderTypes + piBinderTypes" fun o => (((o.setBool `pp.coercions.types true).setBool `pp.numericTypes true).setBool `pp.funBinderTypes true).setBool `pp.piBinderTypes true
