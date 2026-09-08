# Adversarial fixture graph (F01-T4)

Copies of the honest interior nodes and root (`root-chain`) plus four nodes that each exercise
steps 7-8: `wrong-witness` (step 7: witness type `∃ p, p`), `undeclared-dep` (step 8: declares
only `root-chain`, but uses `and-reassoc`'s lemma, which is visible transitively through
`root-chain`'s imports), `unused-dep` (step 8 passes with a warning: declares both, uses neither),
`context-mismatch` (step 8: Context's signature for the tutorial node differs from its Statement).
