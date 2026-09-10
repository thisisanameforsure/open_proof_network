# Proposal fixtures (F08-T1)

Candidate nodes for the `propositional` fixture graph, whose root is `and-swap-reassoc`:

    theorem OpnProp.and_swap_reassoc :
      ∀ p q r : Prop, p ∧ q → (p ∧ q) ∧ r → q ∧ (p ∧ r)

One directory per case `opn-gate admit` has to get right — the accepting one and the refusing one
for each rule in F08-R1's order. Each is a complete D-3 node directory except that the ones meant
to fail are broken in exactly one way, named by the directory.

`test_admit.py` runs them against the fake toolchain (the ordering and the decisions);
`test_admit_lean.py` runs them against the real one (AC18), where the statements, witnesses and
relation proofs actually have to elaborate.

The `.gitkeep` files are D-3's required empty directories (`attempts/`, `annex/`, `explainer/`).
