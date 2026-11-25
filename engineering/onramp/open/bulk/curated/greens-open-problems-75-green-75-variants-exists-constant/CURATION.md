# green_75.variants.exists_constant — variant of live target `green-75`

**Decision: D-30 variant of the live root node `green-75` (target `green-75`), label `partial`.**
Not a new target.

Row: `fc:FormalConjectures/GreensOpenProblems/75.lean#green_75.variants.exists_constant`
(registry pin d8d031d4998c78575159ccab9a7a9e95ce043883, `research open, question`).

## Facts
- Parent `green_75` is `research open` upstream and live on the graph as `green-75` (root node
  `green-75`, `Opn.green_75`).
- The variant replaces the root's constant 100 by an existentially chosen constant C. The root
  implies it (take C = 100), so the label is `partial` (`<root's type> → <variant's type>`).
  Proving the variant does not settle the root; refuting it would (the registry says
  "`green_75` implies it with C = 100").

## Files (`variant/`), for `POST /proposals/variant`
- `Statement.lean`: the root's header and imports (the target's own `Defs.*`, including
  `Defs.Local` with `imbalance`), `open scoped Finset` / `open Green75` as on the root, and
  `theorem Opn.green_75_exists_constant` whose type is the registry's text byte for byte.
- `Witness.lean`: `theorem witness : True := trivial` (no binders, no leading hypotheses; step 7's
  rule in `gate/lean/OpnGate/WitnessType.lean`).
- `Relation.lean`: `theorem relation : <root's type> → <variant's type>`, proved with C = 100.
  Send as `relation: "partial"`, `relation_proof` = this file; the service writes the
  `-- relation:` line.
- `hazards.yaml`: `off-by-one-range` at `2 ≤ #X`, the same finding the root acknowledges.
- `deps: []`.

## Differences from the registry text
- Theorem name `Opn.green_75_exists_constant` (the registry's `green_75.variants.exists_constant`;
  the driver's last-segment rule would give `Opn.exists_constant`, which says nothing). Name only.
- Module doc line written for the variant. Nothing in the proposition changed.

## Checks
- Compile: one file = `import Mathlib`, `set_option autoImplicit false`,
  `set_option relaxedAutoImplicit false`, the live `targets/green-75/defs/Local.lean` body,
  statement, witness, relation → `POST /check` (log `01M89G39M8SX6BW22DBP6FARCE`): errors `[]`,
  only warning `declaration uses sorry` (the statement).
- Hazards: `POST /check` mode `hazards` with `target_id: green-75` could not run: the service's
  inlining of green-75's seven defs modules fails on its own (`Function expected at ι` inside the
  inlined `FieldTheoryMilnorKTheory`, a section variable leaking from an earlier inlined module;
  logs `01M89FP4QG2QQSN0Q65AKE9PSN`, `01M89FQJM821MKWC8A3Y7WMQ0C`). This is a service defect,
  not the statement's: it affects every witness/hazards pre-flight on green-75 (and likely every
  target carrying the Clique/Coloring modules). Probed instead with `imbalance` inlined
  (`01M89FYBDRT3TCQVPDQRQHXPRH`): one finding, `off-by-one-range` at `2 ≤ #X`, acknowledged.
  Because the proposal route runs this same pre-flight, the lead should expect
  `hazards_preflight: inconclusive` / `witness_preflight: inconclusive` (or a
  `422 statement-fails`) on this proposal until the inlining is fixed.

Sources read: the registry file; graph-ref `targets/green-75/` (Statement, META, Witness,
defs/Local.lean); AGENTS.md §Proposals (D-29, D-30); `OpnGate/WitnessType.lean`.
