import OpnGate.Frontend
import OpnGate.Hazards

/-! `auto-implicit` (F02-T9): an identifier the statement never declares. With `autoImplicit` on —
Lean core's default, inherited by the gate's elaboration, which passes no options — an unbound
name becomes an implicit binder the author did not write (`theorem t : n + 0 = n` is
`∀ {n : Nat}, n + 0 = n`; `foo = foo` is `∀ {α : Sort u} {foo : α}, foo = foo`), so a statement
quantifies over something invisible, and a misspelt constant reads as a variable (two testers,
2026-09-27).

Nothing in the elaborated type tells an auto-bound binder from a written one (probed at Lean
4.33.1, `engineering/evidence/F02/task-9.txt`), so this checker is not a predicate over subterms:
it elaborates the statement's commands a second time, on the environment its imports already gave
(Frontend's one-import rule), with `autoImplicit := false`, and every message tagged as an unknown
identifier is one finding at that identifier — the shape `unused-binder` uses for a name. -/
open Lean Meta Elab

namespace OpnGate.Hazards

/-- The identifier an unknown-identifier error names, read off the message's tag (the text is
``Unknown identifier `n` `` followed by notes; the name sits between the first backticks). -/
def unknownIdentifier? (m : Message) : IO (Option String) := do
  unless m.severity == .error do return none
  let text ← m.data.toString
  unless m.data.kind == unknownIdentifierMessageTag || text.startsWith "Unknown identifier" do
    return none
  match text.splitOn "`" with
  | _ :: name :: _ => return some name
  | _ => return none

/-- `{n : T}` as the statement's type binds `n` implicitly, when it does: what the author
never wrote, shown back. -/
def boundAs (stmt : Statement) (name : String) : IO (Option String) := do
  let some info := stmt.env.find? stmt.decl | return none
  let ctx : Core.Context := { fileName := stmt.path.toString, fileMap := default }
  let (found, _, _) ← (forallTelescope info.type fun xs _ => do
      for x in xs do
        let d ← x.fvarId!.getDecl
        if d.binderInfo == .implicit && d.userName.toString == name then
          return some (toString (← ppExpr d.type))
      return none : MetaM (Option String)).toIO ctx { env := stmt.env }
  return found

def autoImplicit : Checker where
  id := "auto-implicit"
  describe := "an identifier the statement never declares, bound by autoImplicit as an implicit binder"
  visit _ := pure none
  source := some fun stmt => do
    let opts := ({} : Options).setBool `autoImplicit false
    let (_, log) ← elabFile stmt.path stmt.module (some stmt.base) opts
    let mut out : Array Finding := #[]
    for m in log.toList do
      let some name ← unknownIdentifier? m | continue
      let bound := match ← boundAs stmt name with
        | some ty => s!" as `\{{name} : {ty}}`"
        | none => ""
      out := out.push {
        checker := "auto-implicit", location := name,
        message := s!"`{name}` is not declared: autoImplicit bound it{bound}, an implicit binder the author never wrote; declare it, or correct the name if a constant was meant" }
    return out

end OpnGate.Hazards
