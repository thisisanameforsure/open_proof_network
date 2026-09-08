import Lean

/-!
Step 7's expected witness type (F01-R3, Q1).

For `theorem s : ∀ (x₁ : α₁) … (hₖ : Pₖ), C`, the expected witness type is
`∃ x₁ …, P₁ ∧ … ∧ Pₖ`, where the hypotheses are the binders whose type is a `Prop`; a statement
with no Prop binders gets `True`. A hypothesis that later binders depend on cannot sit inside a
plain conjunction, so it is quantified existentially instead.
-/
open Lean Meta

namespace OpnGate

/-- Close `body` under existential quantifiers over `xs`, innermost last. -/
def mkExistsFVars (xs : Array Expr) (body : Expr) : MetaM Expr := do
  let mut e := body
  for x in xs.reverse do
    let ty ← inferType x
    let u ← getLevel ty
    let lam ← mkLambdaFVars #[x] e
    e := mkApp2 (mkConst ``Exists [u]) ty lam
  return e

/-- Right-nested conjunction `P₁ ∧ (P₂ ∧ … Pₖ)`; `True` when there is nothing to conjoin. -/
def mkAndChain (ps : Array Expr) : Expr :=
  go ps.toList
where
  go : List Expr → Expr
    | [] => mkConst ``True
    | [p] => p
    | p :: rest => mkAnd p (go rest)

/-- The expected witness type for a statement of type `stmtType`. -/
def expectedWitnessType (stmtType : Expr) : MetaM Expr := do
  forallTelescope stmtType fun xs _concl => do
    let n := xs.size
    -- A Prop binder is a hypothesis unless some later binder's type mentions it.
    let mut isHyp : Array Bool := #[]
    for i in [0:n] do
      let x := xs[i]!
      let t ← inferType x
      let mut hyp ← isProp t
      if hyp then
        for j in [i + 1:n] do
          let tj ← inferType xs[j]!
          if tj.containsFVar x.fvarId! then hyp := false
      isHyp := isHyp.push hyp
    let vars := (xs.zip isHyp).filterMap fun (x, h) => if h then none else some x
    let hypTypes ← (xs.zip isHyp).filterMapM fun (x, h) =>
      if h then return some (← inferType x) else return none
    let body := mkAndChain hypTypes
    let closed ← mkExistsFVars vars body
    instantiateMVars closed

end OpnGate
