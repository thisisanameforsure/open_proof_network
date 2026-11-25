# green_76.variants.exists_constant — variant of live target `green-76`

**Decision: D-30 variant of the live root node `green-76` (target `green-76`), label `partial`.**
Not a new target.

Row: `fc:FormalConjectures/GreensOpenProblems/76.lean#green_76.variants.exists_constant`
(registry pin d8d031d4998c78575159ccab9a7a9e95ce043883, `research open, question`).

## Facts
- Parent `green_76` is `research open` upstream and live as `green-76` (root `Opn.green_76`).
- The variant replaces the root's threshold 1000 by an existentially chosen k (Pach–Tardos,
  Problem 5, in an equivalent form). The root implies it (k = 1000): label `partial`.

## Files (`variant/`)
- `Statement.lean`: root's header/imports (`Defs.Local` has `HitsRichRectangles`),
  `open scoped Finset` / `open Green76`, `theorem Opn.green_76_exists_constant`, type byte for byte
  the registry's.
- `Witness.lean`: `True := trivial` (no binders).
- `Relation.lean`: `relation : <root's type> → <variant's type> := fun h => ⟨1000, h⟩`;
  send `relation: "partial"`.
- No `hazards.yaml`: the checkers report no findings.
- `deps: []`.

## Differences from the registry text
- Theorem name `Opn.green_76_exists_constant`; module doc line. Proposition unchanged.

## Checks
- Compile (autoImplicit off, live `targets/green-76/defs/Local.lean` inlined, statement + witness
  + relation): `POST /check` log `01M89G3AKGVZD609CEJ957PB49`, errors `[]`.
- Hazards: `POST /check` mode `hazards`, `target_id: green-76`, the real statement
  (`01M89FQQGG10GR391JPBYRFPY9`): `hazards_status: ran`, findings `[]`.

Sources: the registry file; graph-ref `targets/green-76/`; AGENTS.md §Proposals.
