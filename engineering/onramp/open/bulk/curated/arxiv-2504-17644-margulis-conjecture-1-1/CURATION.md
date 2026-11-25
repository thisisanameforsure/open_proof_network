# arxiv-2504-17644-margulis-conjecture-1-1 — declined

Row: `fc:FormalConjectures/Arxiv/2504.17644/Margulis.lean#conjecture_1_1` at registry commit d8d031d4998c78575159ccab9a7a9e95ce043883.
Curator A, 2026-11-25.

## Decision: declined (the non-vacuity witness is research-level mathematics to formalize)

The statement itself is portable. Its only name outside Mathlib is
`Matrix.SpecialLinearGroup.diagonalSubgroup`, from
`FormalConjecturesForMathlib/LinearAlgebra/SpecialLinearGroup.lean`. That module imports
`FormalConjecturesForMathlib/LinearAlgebra/GeneralLinearGroup.lean`, which defines `diagonalHom` and
`diagonalSubgroup`. Neither has a `sorry`, an `axiom` or an `opaque`. The file's own definition
(`polyToLaurent`) is not used by `conjecture_1_1`, and the section's `variable (n …) (R …)` is shadowed
by the theorem's own `{n : ℕ}`. The driver's "cross-file" flag comes from `open Matrix`, a namespace
some registry file also extends. The statement does not use any registry declaration in it.

The row cannot be imported because of the D-4 step 7 witness. The theorem's binders carry two
hypotheses, `hn : 3 ≤ n` and
`hg : IsCompact (closure (MulAction.orbit (diagonalSubgroup (Fin n) ℝ) g))`. Step 7 would expect
(per `gate/lean/OpnGate/WitnessType.lean`)

    ∃ (n : ℕ) (g : SL(n, ℝ) ⧸ Subgroup.map (map (Int.castRingHom ℝ)) ⊤),
      3 ≤ n ∧ IsCompact (closure (MulAction.orbit (diagonalSubgroup (Fin n) ℝ) g))

That is the existence, for some n ≥ 3, of a lattice in `SL_n(ℝ)/SL_n(ℤ)` whose diagonal orbit is
relatively compact. It is true. The standard examples are the compact orbits of lattices coming from
full modules in a totally real number field of degree n, by Dirichlet's unit theorem and Mahler's
criterion. But no shortcut exists: the identity coset's orbit is unbounded, since `diag(t, 1/t, 1, …)`
shrinks `e₁`. A proof in Lean would be a real formalization (a totally real cubic field, its unit
lattice, and compactness in the quotient topology), which is new mathematics for the network, not
curation (brief rule 5).

## What the lead could decide

The ports would be `defs/LinearAlgebraGeneralLinearGroup.lean` and `defs/LinearAlgebraSpecialLinearGroup.lean`,
both mechanical, with the statement as the registry wrote it. Only the witness is missing. If someone
writes it, nothing else blocks the row.

## Sources read
- `FormalConjectures/Arxiv/2504.17644/Margulis.lean`
- `FormalConjecturesForMathlib/LinearAlgebra/SpecialLinearGroup.lean`, `…/GeneralLinearGroup.lean`
- `gate/lean/OpnGate/WitnessType.lean` (how step 7 forms the expected type)

## Checks
None sent: there is nothing to import without the witness.
