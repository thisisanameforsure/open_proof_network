# millennium-bsd-weierstrass-curve-affine-rat-weak-bsd — import as stated

Row: `fc:FormalConjectures/Millennium/BSD.lean#WeierstrassCurve.Affine.Rat.weakBSD` at registry commit d8d031d4998c78575159ccab9a7a9e95ce043883. Curator A, 2026-11-25.

## Decision: import as stated, with hand ports of two registry files

The statement is `WeakBSD E`. Its meaning depends on two registry files:
- `FormalConjectures/Millennium/BSD.lean` (its own file) defines
  `WeakBSD E := ∃ L : ℂ → ℂ, HasMeromorphicContinuation E L ∧ meromorphicOrderAt L 1 = Module.finrank ℤ E.Point`;
- `FormalConjectures/Wikipedia/HasseWeil.lean` (namespace `HasseWeil`, opened by BSD.lean) defines
  `HasMeromorphicContinuation E L := Meromorphic L ∧ ∀ s : ℂ, 3 / 2 < s.re → L s = E.LSeries s`.

`WeierstrassCurve.LSeries`, `Meromorphic`, `meromorphicOrderAt`, `Module.finrank` and
`WeierstrassCurve.Affine.Point` are all Mathlib. No `FormalConjecturesForMathlib` module is needed. The
third import of BSD.lean, `FormalConjectures/Wikipedia/EllipticCurveRank.lean`, is used only through
`attribute [local instance] EllipticCurveRank.mordell_weil`, a `Module.Finite ℤ E.Point` instance that
the registry leaves unproved. `WeakBSD` never asks for it: `Module.finrank` needs no finiteness
instance, and the compile below runs without the attribute. So it is not ported. The driver's
refusal "cannot port … EllipticCurveRank" does not apply to the weak statements. It does apply to the
strong ones, which are declined (see `…-strong-bsd/CURATION.md`).

The ports are identical for both weak rows (`cmp`-checked against `…-number-field-weak-bsd/defs/`).

## Differences from the registry's text
- `theorem weakBSD` is `theorem Opn.weakBSD`, lifted out of its namespaces. Its binders are
  `(E : Affine ℚ) [E.IsElliptic]` (the `namespace Rat` section variables, both used), and the conclusion is byte for byte. The statement opens `open WeierstrassCurve WeierstrassCurve.Affine` so that `Affine` and
  `WeakBSD` (or `NumberField.WeakBSD`) resolve to the same constants they name inside the registry's
  namespaces. `open WeierstrassCurve` is needed because `Affine` was resolved inside
  `namespace WeierstrassCurve.Affine`.
- `defs/WikipediaHasseWeil.lean`: HasseWeil.lean's two definitions (`HasMeromorphicContinuation`,
  `HasAnalyticContinuation`), byte for byte with their docstrings, `variable` line and scope lines,
  plus the module doc and header. Removed: `module` (written `module ` with a trailing space there),
  `public import FormalConjecturesUtil` (it becomes `import Mathlib`), `@[expose] public section`
  (it becomes `section`), the two proved API lemmas (`@[category API]`, an attribute that does not
  exist under Mathlib alone; no definition uses them), and the three conjectures.
- `defs/Local.lean`: BSD.lean's `WeakBSD` with its docstring, the `namespace WeierstrassCurve.Affine`
  / `open Projective HasseWeil NumberField` / `namespace NumberField` / `variable …` lines, the
  module doc and header, and `import Defs.WikipediaHasseWeil`. Removed beyond the module syntax:
  1. `attribute [local instance] EllipticCurveRank.mordell_weil`, whose source theorem is unproved
     and which `WeakBSD` does not use;
  2. `bsdQuotient` and `StrongBSD`, which need that instance (`Point.regulator` takes
     `[Module.Finite ℤ (W.Point ⧸ torsion)]`) and which no weak statement uses;
  3. the conjectures and the test `StrongBSD.weakBSD`. The empty `namespace Rat` section, which
     holds only theorems, is dropped too.
  No `sorry`, `axiom` or `opaque` remains in either port (grep-checked).
- Witness: `∃ (E : WeierstrassCurve.Affine ℚ), E.IsElliptic`, with the curve y² = x³ - x (a₄ = -1, every other coefficient 0, Δ = 64).

## Checks
- `POST /check` (mode check). Sent: `import Mathlib`, `autoImplicit` and `relaxedAutoImplicit`
  off, WikipediaHasseWeil then Local each in a section, then the statement and the witness. Result:
  `lean_messages.errors == []`, and the only warning is the statement's `sorry`. For the
  number-field row, a probe `example : (∃ (K : Type _) … , NumberField K ∧ E.IsElliptic) := witness`
  also compiled, and `#print axioms witness` gave [propext, Classical.choice, Quot.sound].
- `POST /check` (mode hazards, the inlined text up to the witness, sent as `statement`). It reported
  two `auto-implicit` findings, at `Affine` and at `HasMeromorphicContinuation`. I believe these
  are artifacts of sending the defs inlined as part of the "statement". The checker re-elaborates
  the text's commands with `autoImplicit := false`, and in the defs those names resolve only inside
  `namespace WeierstrassCurve.Affine` and under `open HasseWeil`. `HasMeromorphicContinuation`
  never appears in the statement itself. The full file compiled with `autoImplicit false` and no
  error, so no binder is silent. I did **not** write a `hazards.yaml`. If step 6 at admission (where
  the defs are imported modules, not inlined text) still reports these, the lead should look; I
  expect it will not.

## Sources read
`FormalConjectures/Millennium/BSD.lean`, `FormalConjectures/Wikipedia/HasseWeil.lean`,
`FormalConjectures/Wikipedia/EllipticCurveRank.lean`,
`FormalConjecturesForMathlib/AlgebraicGeometry/EllipticCurve/*.lean`, `gate/tools/wave.py`,
`gate/lean/OpnGate/WitnessType.lean`, `gate/lean/OpnGate/Hazards/AutoImplicit.lean`, `targets/abc`.
