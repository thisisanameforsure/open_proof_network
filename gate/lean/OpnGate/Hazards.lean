import Lean

/-!
Step 6's checker framework (F02-R1, R2, R10; Q3).

A checker looks at one subterm of the statement's type at a time, inside the local context of
the binders above it, and answers with a message when that subterm is a hazard. The framework
walks every subterm once, collects `{checker, location, message}` findings, deduplicates and
sorts them so two runs print byte-identical output (R10), and caps them (budgets §6).

The `location` is the offending subterm pretty-printed in its binder context (`n - 1`, `a / b`):
that is what a proposer writes into `META.yaml` to acknowledge it, and it survives whitespace
edits to the file where a line:column would not (F02-Q4).
-/
open Lean Meta

namespace OpnGate.Hazards

structure Finding where
  checker : String
  location : String
  message : String
deriving ToJson, BEq, Repr

def Finding.lt (a b : Finding) : Bool :=
  a.checker < b.checker
    || (a.checker == b.checker
      && (a.location < b.location || (a.location == b.location && a.message < b.message)))

/-- What a checker says about one subterm: a message, and a location when the subterm itself is
not the right one to name (a binder's name rather than the whole `∀`). -/
structure Hit where
  message : String
  location : Option String := none

/-- The statement as a file (F02-T9), for a checker whose question is not about one subterm:
where it is, what module and declaration it is, the environment its imports gave before any of
its commands (so it can be elaborated again without a second import) and the environment with
it elaborated, where `decl` lives. -/
structure Statement where
  path : System.FilePath
  module : Name
  decl : Name
  env : Environment
  /-- The statement's commands elaborated once more under `opts`, answered as their log: what a
  file-level checker reads (`auto-implicit`). `opn-hazards` answers with the file on the
  once-imported environment (`Frontend.elabFile`); the network's hosted program, which inlines
  these files with their imports stripped, answers with the statement's own text on the current
  environment. The checker files import nothing but `Lean` and these modules, so both can. -/
  reelaborate : Options → IO MessageLog

/-- A check over the statement as a file rather than over its type's subterms (F02-T9). -/
abbrev SourceCheck := Statement → IO (Array Finding)

/-- A checker: an id (the `gate-spec.json` name) and a predicate over one subterm — plus, for a
hazard no subterm shows (`auto-implicit`), a check over the file, whose findings join the
subterm findings before deduplication, sorting and the cap (R10). -/
structure Checker where
  id : String
  describe : String
  visit : Expr → MetaM (Option Hit)
  source : Option SourceCheck := none

/-- Findings per statement are capped (F02 §6). -/
def cap : Nat := 200

-- Shared term shape helpers --------------------------------------------------------------

def isNat (e : Expr) : Bool := e.isConstOf ``Nat

def isInt (e : Expr) : Bool := e.isConstOf ``Int

/-- `n` when `e` is the raw literal `n` or `OfNat.ofNat _ n _`. -/
def natLit? (e : Expr) : Option Nat :=
  match e with
  | .lit (.natVal n) => some n
  | _ =>
    if e.isAppOfArity ``OfNat.ofNat 3 then
      match e.getAppArgs[1]! with
      | .lit (.natVal n) => some n
      | _ => none
    else none

/-- The constant at the head of an application, or `Name.anonymous`. -/
def headName (e : Expr) : Name :=
  (e.getAppFn.constName?).getD .anonymous

/-- Leading binders of a type: the number of arguments a full application supplies. -/
def countForalls : Expr → Nat
  | .forallE _ _ b _ => countForalls b + 1
  | _ => 0

/-- `e` is a constant applied to exactly as many arguments as its type binds — so a checker
matching a function by name fires once, on the full application, never on its partial ones. -/
def fullyApplied (e : Expr) : MetaM Bool := do
  let n := headName e
  if n.isAnonymous then return false
  let some info := (← getEnv).find? n | return false
  return e.getAppNumArgs == countForalls info.type

/-- A binary heterogeneous operator application `Op.op α β γ inst a b`: `(α, a, b)`. -/
def binOp? (e : Expr) (op : Name) : Option (Expr × Expr × Expr) :=
  if e.isAppOfArity op 6 then
    let args := e.getAppArgs
    some (args[0]!, args[4]!, args[5]!)
  else none

-- The walk ---------------------------------------------------------------------------------

/-- Visit every subterm of `e` with every checker, binders entered so fvars have types. -/
partial def traverse (checkers : Array Checker) (e : Expr) : MetaM (Array Finding) := do
  let mut out : Array Finding := #[]
  for c in checkers do
    if let some hit ← c.visit e then
      let location ← match hit.location with
        | some l => pure l
        | none => do pure (toString (← ppExpr e))
      out := out.push { checker := c.id, location, message := hit.message }
  match e with
  | .app f a =>
    return out ++ (← traverse checkers f) ++ (← traverse checkers a)
  | .forallE n t b bi =>
    let inT ← traverse checkers t
    let inB ← withLocalDecl n bi t fun x => traverse checkers (b.instantiate1 x)
    return out ++ inT ++ inB
  | .lam n t b bi =>
    let inT ← traverse checkers t
    let inB ← withLocalDecl n bi t fun x => traverse checkers (b.instantiate1 x)
    return out ++ inT ++ inB
  | .letE n t v b _ =>
    let inT ← traverse checkers t
    let inV ← traverse checkers v
    let inB ← withLetDecl n t v fun x => traverse checkers (b.instantiate1 x)
    return out ++ inT ++ inV ++ inB
  | .mdata _ b => return out ++ (← traverse checkers b)
  | .proj _ _ b => return out ++ (← traverse checkers b)
  | _ => return out

/-- Deduplicated, sorted, capped findings over a statement type (R10), together with `extra`,
what the selected checkers' file-level checks found (F02-T9). -/
def run (checkers : Array Checker) (stmtType : Expr) (extra : Array Finding := #[])
    : MetaM (Array Finding × Bool) := do
  let raw := (← traverse checkers stmtType) ++ extra
  let mut uniq : Array Finding := #[]
  for f in raw do
    unless uniq.contains f do uniq := uniq.push f
  let sorted := uniq.qsort Finding.lt
  if sorted.size > cap then
    return (sorted.extract 0 cap, true)
  return (sorted, false)

end OpnGate.Hazards
