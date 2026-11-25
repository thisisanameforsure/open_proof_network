# dixmier_conjecture.variants.dimension_one — own target (parent disproved)

**Decision: import as its own target (Dixmier's Problem 1), stated as the registry states it,
titled as the dimension-one case of the Dixmier conjecture.**

Row: `fc:FormalConjectures/Arxiv/math.0608009/DixmierConjecture.lean#dixmier_conjecture.variants.dimension_one`
(registry pin d8d031d4998c78575159ccab9a7a9e95ce043883, `research open`).

## Facts
- Parent `dixmier_conjecture : ¬ ∀ n, DixmierConjectureFor K n` is `research solved`: DC_n is
  **false** for n ≥ 3 (via Alpöge's 2026 Jacobian counterexample and DC_n ⇒ JC_n). Not a target,
  not live. DC_1 is Dixmier's own 1968 Problem 1 and is open: the natural target.
- Sibling `dimension_two` is also `research open` (not in my rows). DC_1 is implied by PC_1 over
  all char-0 fields (AvdE07 Thm 7) — see the Poisson row; the two targets are related but neither
  is a D-30 variant of the other as stated (the implication quantifies over all fields).

## Proposed record
- title: `Dixmier's Problem 1: the Dixmier conjecture in dimension one (a variant of the Dixmier
  conjecture)`
- informal: `Over a field K of characteristic zero, every endomorphism of the first Weyl algebra
  A₁(K) is an automorphism (Dixmier 1968, Problem 1). The Dixmier conjecture in all dimensions is
  false (it fails for every n ≥ 3); dimension one remains open. It is implied by the Poisson
  conjecture in dimension one and hence by the two-variable Jacobian conjecture.`
- source: formal-conjectures `FormalConjectures/Arxiv/math.0608009/DixmierConjecture.lean`,
  Apache-2.0; Dixmier, Bull. SMF 96 (1968); arXiv:math/0608009.

## Files
- `defs/AlgebraWeylAlgebra.lean`: the live graph's existing port of
  `FormalConjecturesForMathlib/Algebra/WeylAlgebra.lean`, copied unchanged (identical md5 across
  all 194 live targets that carry it).
- `defs/Local.lean`: `DixmierConjectureFor` with the file's two `variable` lines byte for byte, in
  the file's namespace; header and module doc kept; module syntax stripped.
- `Statement.lean`: `open Arxiv.«math.0608009»`, `theorem Opn.dixmier_conjecture_dimension_one
  {K : Type*} [Field K] [CharZero K] : DixmierConjectureFor K 1` — the registry's type, with the
  file's section variables as leading binders (the driver's `used_variables` rule).
- `Witness.lean`: `∃ (K : Type u_1) (inst : Field K), CharZero K := ⟨ULift ℚ, inferInstance,
  RingHom.charZero (ULift.ringEquiv : ULift ℚ ≃+* ℚ).toRingHom⟩`. Uses the auto-bound universe
  `u_1`, as the live merged witness of `projective-module-is-stably-free` does; under
  `autoImplicit false` it needs `universe u_1` first (verified that way).
- No `hazards.yaml` (no literal comparisons; not scannable before the target exists).

## Differences from the registry text (all in the port, none in the proposition)
- The file's `open JacobianConjecture` is left out of the port and the statement:
  `JacobianConjecture` is another registry file's namespace (Wikipedia/JacobianConjecture.lean,
  which would need `RegularFunction` and `name_poly_vars` ported); nothing used here comes from it,
  and without the namespace the `open` line does not elaborate. This is the driver's "opens
  another registry file's namespace" refusal, resolved by dropping a no-op `open`.
- The file's import of `PoissonConjecture.lean` is not carried (unused by the definition).
- Theorem name `Opn.dixmier_conjecture_dimension_one`; module doc.

## Checks
- Compile (autoImplicit off, WeylAlgebra + Local + statement + `universe u_1` + witness):
  `POST /check` log `01M89G2S10YB2KPR8E4K6WKXR9`, errors `[]`.
- Witness type: `POST /check` mode `witness` on a probe with the same binders
  (`01M89G1YN80C7T239N6YK8XF3C`): expected `∃ (K : Type u_1) (inst : Field K), CharZero K`,
  `matches: true`, axioms standard. (`OpnGate/WitnessType.lean` uses `forallTelescope`, which
  does not unfold `DixmierConjectureFor`, so the probe's binders are the real ones.)

Sources: both registry files (Dixmier, Poisson), Wikipedia/JacobianConjecture.lean,
FormalConjecturesForMathlib WeylAlgebra; graph-ref projective-module-is-stably-free.
