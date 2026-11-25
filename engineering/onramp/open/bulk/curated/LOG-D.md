# Curator D log

Rows: `curate-D.json` (eight `.variants.` rows: Maxwell, Dixmier, Poisson, Green 41, Green 75,
Green 76, Kurepa, new Mersenne). Registry pin d8d031d4998c78575159ccab9a7a9e95ce043883.

- 2026-11-25T13:51Z — started; read the brief, the rows, the six registry files (plus
  PoissonBracket.lean and Wikipedia/JacobianConjecture.lean), wave.py's port_body and draft_row,
  AGENTS.md §"Proposals (D-29, D-30)" and §"Iterating fast: POST /check", and graph-ref targets
  green-75, green-76, new-mersenne-conjecture, projective-module-is-stably-free (instance-binder
  witness) and erdos-849/variant-3969f1f7 (a live Relation.lean).
- 2026-11-25T13:52Z — facts. Parents live on the graph: `green-75`, `green-76`,
  `new-mersenne-conjecture` (all three `research open` upstream). Parents not live:
  `maxwell_conjecture` (upstream `research solved`, disproved: `¬ Conjecture`),
  `dixmier_conjecture` and `poisson_conjecture` (both `research solved`, disproved over all n),
  `green_41` (`research open, question value`, stated against `green_41.answer := sorry`, so not
  importable as stated), `kurepa_conjecture` (`research open`, not imported: the catalog's row for
  Paper/Kurepa.lean is the variant).
- 2026-11-25T13:52:54Z — green-75 variant: `/check` witness mode, target green-75 (log
  01M89FP4QG2QQSN0Q65AKE9PSN): 12 errors, all inside the *service's* inlined green-75 defs
  (`Function expected at ι` in FieldTheoryMilnorKTheory; a section variable leaking between
  inlined modules). Not the statement. Switched to composing files myself (Local.lean only).
- 2026-11-25T13:53:07Z — check mode, defs + statement + witness + relation: green-75 variant,
  green-76 variant, new-Mersenne variant (`resolves`, the registry's `grind` proof): errors [] ×3.
- 2026-11-25T13:53:47Z — hazards mode on real statements: new-mersenne (01M89FQ308TC9SSY70EH4G138Q)
  ran, [] ; green-76 (01M89FQQGG10GR391JPBYRFPY9) ran, [] ; green-75 (01M89FQJM821MKWC8A3Y7WMQ0C)
  statement-failed (same inlining defect).
- 2026-11-25T13:54:36Z — Kurepa: defs (plain `notation`) + statement + witness compile (later rerun
  with sanity examples, 01M89G3DH8B90N74C4TCET6WK0, errors []). Witness probe on host
  new-mersenne-conjecture (01M89FSH48Y1JWSM3HGKEJSFRQ): matches. Hazards probe
  (01M89FSK2R32AS1FFQESA3PDBT): off-by-one `2 < p`, div-zero on the modulo.
- 2026-11-25T13:55:46Z — Maxwell: defs + statement + witness, errors [] (01M89FVCPGCMNTHVWZDX8YY6J3).
  Hazards probe: first malformed (my probe error), rerun (01M89FWBYGDZQ6SD9PCRKM5XQ0) ran, [].
- 2026-11-25T13:56:29Z — Green 41 hazards probe: three calls (two of my probes did not elaborate),
  final (01M89FWPP8ERDGD4AY4AMN95FK) ran: `Set.Ioc 0 ε₀`. 13:57:07Z compile, errors []
  (01M89FXTTGFCC8WPR24AF91WKH).
- 2026-11-25T13:57:24Z — green-75 variant hazards via inlined-imbalance probe
  (01M89FYBDRT3TCQVPDQRQHXPRH): `2 ≤ #X`, acknowledged as on the root.
- 2026-11-25T13:58:52Z — Dixmier witness probe 1: ULift ℚ has no CharZero instance found; probe 2
  (01M89G1YN80C7T239N6YK8XF3C) with `RingHom.charZero (ULift.ringEquiv …)`: matches.
- 2026-11-25T13:59:37Z — Dixmier / Poisson compile: `unknown universe level u_1` under autoImplicit
  false (the witness's auto-bound universe, as on the live projective-module witness); rerun with
  `universe u_1` before the witness: errors [] both (01M89G2S10YB2KPR8E4K6WKXR9,
  01M89G2TZGWKHPYT07J435NNJ8).
- 2026-11-25T14:00:09Z — reran green-75/76/Mersenne compiles with autoImplicit off (they had run
  before the header was added): errors [] ×3 (01M89G39M8SX6BW22DBP6FARCE, 01M89G3AKGVZD609CEJ957PB49,
  01M89G3CJ0C6RTE2CYGDMV9KRR). Total `/check` calls: 29.
- 2026-11-25T14:03Z — decisions: green-75, green-76 → `partial` variants of the live roots;
  new-Mersenne → `resolves` variant of the live root; Maxwell, Dixmier, Poisson (parents
  disproved), Green 41 (parent asks for an unknown function), Kurepa (parent open, not imported)
  → own targets titled as variants. CURATION.md written for all eight. Probe files and responses
  in scratchpad `curD/`.
