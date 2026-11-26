# poisson_conjecture.variants.dimension_one — own target (parent disproved)

**Decision: import as its own target, stated as the registry states it, titled as the
dimension-one case of the Poisson conjecture.**

Row: `fc:FormalConjectures/Arxiv/math.0608009/PoissonConjecture.lean#poisson_conjecture.variants.dimension_one`
(registry pin d8d031d4998c78575159ccab9a7a9e95ce043883, `research open`).

## Facts
- Parent `poisson_conjecture : ¬ ∀ n, PoissonConjectureFor K n` is `research solved`: PC_n is
  **false** for every n ≥ 2 (Long 2026 for n = 2; Alpöge 2026 for n ≥ 3). Not a target, not live.
  Only n = 1 is open: the natural target.
- Related to the Dixmier row (PC_1 over all char-0 fields ⇒ DC_1), not a D-30 variant of it.

## Proposed record
- title: `The Poisson conjecture in dimension one (a variant of the Poisson conjecture)`
- informal: `Over a field K of characteristic zero, every endomorphism of the first canonical
  Poisson algebra — the polynomial algebra K[X₁, X₂] with the bracket {X₁, X₂} = 1 — is an
  automorphism. The Poisson conjecture is false in every dimension n ≥ 2; dimension one remains
  open. It is implied by the two-variable Jacobian conjecture and implies Dixmier's Problem 1.`
- source: formal-conjectures `FormalConjectures/Arxiv/math.0608009/PoissonConjecture.lean`,
  Apache-2.0; arXiv:math/0608009.

## Files
- `defs/AlgebraMvPolynomialPoissonBracket.lean`: port of the library module
  `FormalConjecturesForMathlib/Algebra/MvPolynomial/PoissonBracket.lean`, lemmas included (the
  driver's library-module rule), body checked identical to the source by `diff`; its two `public
  import Mathlib.…` lines become `import Mathlib`.
- `defs/Local.lean`: `IsPoissonEndomorphism`, `PoissonConjectureFor` and the file's `variable`
  lines byte for byte; the file's API lemmas and tests dropped (driver's cut).
- `Statement.lean`: `open MvPolynomial`, `open Arxiv.«math.0608009»`, `theorem
  Opn.poisson_conjecture_dimension_one {K : Type*} [Field K] [CharZero K] :
  PoissonConjectureFor K 1`.
- `Witness.lean`: as for Dixmier: `∃ (K : Type u_1) (inst : Field K), CharZero K` via `ULift ℚ`.
- No `hazards.yaml`.

## Differences from the registry text
- The file's `open MvPolynomial JacobianConjecture` becomes `open MvPolynomial` (port and
  statement): `JacobianConjecture` is another registry file's namespace, not ported, and no name
  here comes from it (same reason as the Dixmier row). The file's import of
  Wikipedia/JacobianConjecture is not carried.
- Theorem name `Opn.poisson_conjecture_dimension_one`; module doc. Proposition unchanged.

## Checks
- Compile (autoImplicit off, PoissonBracket + Local + statement + `universe u_1` + witness):
  `POST /check` log `01M89G2TZGWKHPYT07J435NNJ8`, errors `[]`.
- Witness type: same binders as the Dixmier probe (`01M89G1YN80C7T239N6YK8XF3C`, `matches: true`).

Sources: the registry files; FormalConjecturesForMathlib PoissonBracket.lean.
