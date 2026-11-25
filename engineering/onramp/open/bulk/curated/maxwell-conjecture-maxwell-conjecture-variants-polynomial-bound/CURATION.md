# maxwell_conjecture.variants.polynomial_bound — own target (parent disproved)

**Decision: import as its own target, stated as the registry states it, titled as a question
left by the disproof of the Maxwell conjecture.**

Row: `fc:FormalConjectures/Arxiv/2607.27197/MaxwellConjecture.lean#maxwell_conjecture.variants.polynomial_bound`
(registry pin d8d031d4998c78575159ccab9a7a9e95ce043883, `research open, question`).

## Facts
- Parent `maxwell_conjecture : ¬ Conjecture` is `research solved`: the Maxwell conjecture (at
  most (n−1)² non-degenerate equilibria) is **false** (Arathoon–Ball–Kvalheim 2026, 24 > 16 for
  five charges). It cannot be a target and is not live. The variant is a genuinely open question
  in its own right (known bounds: ≥ 10n asymptotically below, exponential above).
- Sibling `maxwell_conjecture.variants.three_charges` is also `research open` (not in my rows).

## Proposed record
- title: `Polynomial bound on equilibria of point charges (a variant of the Maxwell conjecture)`
- informal: `Is the number of equilibria of n point charges bounded by a polynomial in n? That is:
  are there constants C, d such that for every n ≥ 1, every configuration of n non-zero point
  charges at distinct points of ℝ³ whose equilibria (critical points of the Coulomb potential
  V(x) = Σ q_j/|x − a_j| away from the charges) are all non-degenerate has at most C·n^d of them?
  Maxwell's conjecture, the bound (n−1)², was disproved by Arathoon, Ball and Kvalheim (2026); the
  best known upper bounds are exponential in n.`
- source: formal-conjectures `FormalConjectures/Arxiv/2607.27197/MaxwellConjecture.lean`,
  Apache-2.0; arXiv:2607.27197; arXiv:2501.05315.

## Files
- `defs/Local.lean`: all of the file's definitions byte for byte (`potential`,
  `HasNondegenerateHessianAt`, `equilibria`, `nondegenerateEquilibria`, `Conjecture`,
  `counterexamplePositions`, `counterexampleCharges`, `phiZero`) with the file's namespace and
  `open scoped Gradient`, theorems and tests dropped — the driver's cut (`port_body`). Header and
  module doc kept; module syntax stripped.
- `Statement.lean`: `open scoped Gradient`, `open Arxiv.«2607.27197»`, `theorem
  Opn.maxwell_conjecture_polynomial_bound`, type byte for byte (checked by `diff` against the
  source lines).
- `Witness.lean`: `True := trivial` (no binders before the colon; the `∃ C d` is the claim).
- No `hazards.yaml`: no findings.

## Differences from the registry text
- Theorem name `Opn.maxwell_conjecture_polynomial_bound`; module doc. Proposition unchanged.

## Checks
- Compile (autoImplicit off, defs + statement + witness): `POST /check` log
  `01M89FVCPGCMNTHVWZDX8YY6J3`, errors `[]`.
- Hazards on a probe with the same binder structure and the definitions replaced by inline
  stand-ins (`01M89FWBYGDZQ6SD9PCRKM5XQ0`, `ran`): findings `[]` (`0 < n` is not flagged). The real
  statement could not be scanned before the target exists; step 6 at intake is the verdict.

Sources: the registry file; wave.py `port_body`.
