import OpnGate.WitnessType

/-!
The type D-12's five resolution artifacts must declare (F07-R4, R5).

A node's statement is `S`. What an artifact has to prove depends on which of the five it is, and
nothing else:

| artifact                       | declared type |
|--------------------------------|---------------|
| proof, partial, reduction      | `S`           |
| counterexample                 | `¬ S`         |
| vacuity certificate            | `¬ W`, `W` the F01 expected witness type |

The gate decides this rather than trusting the submission block: the block is a declaration and
the file is the evidence (F07-Q9).
-/
open Lean Meta

namespace OpnGate

inductive ArtifactKind where
  | proof | counterexample | vacuity | partial_ | reduction
deriving Repr, BEq

def ArtifactKind.ofString? : String → Option ArtifactKind
  | "proof" => some .proof
  | "counterexample" => some .counterexample
  | "vacuity" => some .vacuity
  | "partial" => some .partial_
  | "reduction" => some .reduction
  | _ => none

def ArtifactKind.toString : ArtifactKind → String
  | .proof => "proof"
  | .counterexample => "counterexample"
  | .vacuity => "vacuity"
  | .partial_ => "partial"
  | .reduction => "reduction"

/-- The type this kind of artifact must declare, given the statement's type. -/
def expectedArtifactType (kind : ArtifactKind) (stmtType : Expr) : MetaM Expr := do
  match kind with
  | .proof | .partial_ | .reduction => return stmtType
  | .counterexample => return mkNot stmtType
  | .vacuity => return mkNot (← expectedWitnessType stmtType)

/-!
The relation a labeled variant must prove (D-30; F08-R4).

A variant is a different statement offered beside a target's root, and its label says how the two
are related. Above `related` the label is a claim about implication, and a claim is proved:

* `resolves` — the variant implies the root, `V → R`: proving the variant closes the target.
* `partial` — the root implies the variant, `R → V`: the variant is the weaker statement, so
  proving it is progress and not a resolution.
* `related` — no implication is claimed, so there is nothing to prove and no `Relation.lean`.

Getting the direction wrong is the whole risk the label exists to price, which is why the gate
checks it rather than reading the label.
-/

inductive RelationLabel where
  | resolves | partial_ | related
deriving Repr, BEq

def RelationLabel.ofString? : String → Option RelationLabel
  | "resolves" => some .resolves
  | "partial" => some .partial_
  | "related" => some .related
  | _ => none

def RelationLabel.toString : RelationLabel → String
  | .resolves => "resolves"
  | .partial_ => "partial"
  | .related => "related"

/-- The implication `Relation.lean` must declare, or `none` for `related`, which claims none. -/
def expectedRelationType (label : RelationLabel) (variant root : Expr) : MetaM (Option Expr) := do
  match label with
  | .resolves => return some (← mkArrow variant root)
  | .partial_ => return some (← mkArrow root variant)
  | .related => return none

end OpnGate
