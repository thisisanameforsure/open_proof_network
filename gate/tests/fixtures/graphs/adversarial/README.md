# Adversarial fixture graph (F01-T4)

Copies of the honest interior nodes and root (`root-chain`) plus four nodes that each exercise
steps 7-8: `wrong-witness` (step 7: witness type `∃ p, p`), `undeclared-dep` (step 8: declares
only `root-chain`, but uses `and-reassoc`'s lemma, which is visible transitively through
`root-chain`'s imports), `unused-dep` (step 8 passes with a warning: declares both, uses neither),
`context-mismatch` (step 8: Context's signature for the tutorial node differs from its Statement).

F02-T5 adds `nat-sub-ack` (step 6: a `nat-sub` finding at `n - 0`, acknowledged in a `meta/v2`
META.yaml; the pregate test also runs it with the acknowledgment removed) and switches this
graph's `gate-spec.json` on to all six hazard checkers; the other nodes' statements are
propositional and produce no findings.
