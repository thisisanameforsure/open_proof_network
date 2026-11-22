/-! Non-vacuity witness (D-4 step 7): the statement's leading binders are an implicit type `V`
and a graph `G` on it with no hypothesis, so the expected witness type is their closure over
`True`. Checked against the gate's own expected type on the hosted checker before import
(F14-T18). -/

theorem witness : ∃ (V : Type) (G : SimpleGraph V), True := ⟨Unit, ⊥, trivial⟩
