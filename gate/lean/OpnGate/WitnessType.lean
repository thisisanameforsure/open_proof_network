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

/-- D-29 v3.22 (F07-T44): the expected witness type of a hole whose statement's leading binders
at the indices `proved` were proved by the merged assembly rather than left as holes.

The witness exhibits everything else — the statement's variables, its hypotheses, the hypotheses
inherited from other holes — and is *given* the proved binders: each maximal run of unproved
binders is `∃ vars, hyps ∧ rest` exactly as `expectedWitnessType` builds it, and a run of proved
binders is `∀`-bound in front of `rest`, so a hole hypothesis that sits after a proved fact is
asked for under it (`p → q → q ∧ p`). Where nothing follows a proved run, the run adds nothing.

Why this is sound: every proved binder is a field of a structure the assembly destructured, from
a term over the binders before it (the extractor marks no other kind, `Holes.lean`). Whatever
values a witness gives the binders before it, that term exists, so its fields do, and the
`∀`-bound part holds of them. Step 4 has kernel-checked the assembly that says so.

With `proved` empty this is `expectedWitnessType`, the same expression: a hole with no record
keeps the type it was written with. An index that is not a binder of the statement is an error,
not a silently wider type. -/
def expectedWitnessTypeNarrowed (stmtType : Expr) (proved : Array Nat) : MetaM Expr := do
  if proved.isEmpty then return ← expectedWitnessType stmtType
  forallTelescope stmtType fun xs _concl => do
    let n := xs.size
    for i in proved do
      if i ≥ n then
        throwError "proved binder {i} is not a binder of the statement ({n} binders)"
    -- 0: a variable (∃), 1: a hypothesis (∧), 2: proved (∀). The first two by the rule above.
    let mut kinds : Array Nat := #[]
    for i in [0:n] do
      let x := xs[i]!
      if proved.contains i then
        kinds := kinds.push 2
      else
        let t ← inferType x
        let mut hyp ← isProp t
        if hyp then
          for j in [i + 1:n] do
            if (← inferType xs[j]!).containsFVar x.fvarId! then hyp := false
        kinds := kinds.push (if hyp then 1 else 0)
    -- Segments, from the last: (vars, hyps) of an unproved run, then the proved run after it.
    let mut rest : Expr := mkConst ``True
    let mut i := n
    while i > 0 do
      -- the proved run ending at i
      let mut j := i
      while j > 0 && kinds[j - 1]! == 2 do j := j - 1
      if j < i && !rest.isConstOf ``True then
        rest ← mkForallFVars (xs.extract j i) rest
      -- the unproved run ending at j
      let mut k := j
      while k > 0 && kinds[k - 1]! != 2 do k := k - 1
      if k < j then
        let seg := (xs.extract k j).zip (kinds.extract k j)
        let vars := seg.filterMap fun (x, kd) => if kd == 0 then some x else none
        let hyps ← seg.filterMapM fun (x, kd) =>
          if kd == 1 then return some (← inferType x) else return none
        let conj := if rest.isConstOf ``True then hyps else hyps.push rest
        rest ← mkExistsFVars vars (mkAndChain conj)
      i := k
    instantiateMVars rest

end OpnGate
