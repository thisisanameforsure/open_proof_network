# millennium-bsd-weierstrass-curve-affine-number-field-strong-bsd — declined

Row: `fc:FormalConjectures/Millennium/BSD.lean#WeierstrassCurve.Affine.NumberField.strongBSD`
at registry commit d8d031d4998c78575159ccab9a7a9e95ce043883. Curator A, 2026-11-25.

## Decision: declined (a definition the statement uses rests on `sorry`)

The statement is `StrongBSD E`. Its definition uses `bsdQuotient E`, and `bsdQuotient` (BSD.lean) uses
`Point.regulator E`. That is `WeierstrassCurve.Affine.Point.regulator` from
`FormalConjecturesForMathlib/AlgebraicGeometry/EllipticCurve/Regulator.lean`:

    def regulator [Module.Finite ℤ (W.Point ⧸ Submodule.torsion ℤ W.Point)] : ℝ := …

BSD.lean supplies that instance only through the line

    attribute [local instance] EllipticCurveRank.mordell_weil

and `EllipticCurveRank.mordell_weil` (`FormalConjectures/Wikipedia/EllipticCurveRank.lean`) is a theorem
whose proof is `sorry` (the Mordell–Weil theorem, with a `formal_proof` link to an external
formalization that the registry does not import). So the definition `bsdQuotient`, and therefore
`StrongBSD`, cannot be ported without a `sorry`. Rule 2 forbids that.

The other names `StrongBSD` uses are free of `sorry`: `period` (GlobalPeriod.lean),
`tateShafarevich` (TateShafarevich.lean and RepresentationTheory/Homological/ContCohomology/Sha.lean)
and `tamagawaProduct` (Tamagawa.lean). A grep of `FormalConjecturesForMathlib/AlgebraicGeometry/EllipticCurve/`
finds no `sorry`, `axiom` or `opaque`. The one blocker is the instance.

## What the lead could decide

Because `Module.Finite …` is a `Prop`, the value of `regulator` does not depend on which proof of it
is used. One adapted form would give the statement the binder `[Module.Finite ℤ E.Point]`, which is
Mordell–Weil, a theorem, and port `bsdQuotient`/`StrongBSD` with that instance in scope instead of the
`attribute` line. That changes the Lean text, and formally adds a hypothesis. Under rule 1 it is the
owner's call, not a curator's, so the row is declined here. The weak rows (`…-weak-bsd`) were imported:
`WeakBSD` does not touch the instance.

## Sources read
- `FormalConjectures/Millennium/BSD.lean`, `FormalConjectures/Wikipedia/HasseWeil.lean`,
  `FormalConjectures/Wikipedia/EllipticCurveRank.lean`
- `FormalConjecturesForMathlib/AlgebraicGeometry/EllipticCurve/{Regulator,GlobalPeriod,TateShafarevich,Tamagawa,MinimalDiscriminant}.lean`

## Checks
None sent: there is nothing to import without the instance.
