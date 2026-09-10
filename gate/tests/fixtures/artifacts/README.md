# Artifact fixtures (F07-T2)

D-12's five resolution artifacts against the tutorial node's statement
(`graphs/propositional/targets/propositional/nodes/tutorial-and-swap/Statement.lean`):

    theorem OpnProp.and_swap : ∀ p q : Prop, p ∧ q → q ∧ p

One file per case the gate has to get right — the accepting one and the refusing one for each
rule — driven against the real toolchain by `test_artifacts_lean.py` and pinned in
`golden/artifact-types.json`. They import nothing, because the statement imports nothing: an
artifact may import only what its statement does.

The counterexample and vacuity fixtures have `sorry` bodies, because the tutorial statement is
true and its negation therefore cannot be proved. That is exactly right for what they are here
to test: this check is about the *type* a submission declares. A real submission with a `sorry`
in it is refused by step 5, on its axioms, whatever type it declares.
