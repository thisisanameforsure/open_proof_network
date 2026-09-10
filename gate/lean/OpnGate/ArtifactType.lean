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

end OpnGate
