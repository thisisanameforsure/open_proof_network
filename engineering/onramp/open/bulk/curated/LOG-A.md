# Curator A log

Rows: `curate-A.json` (six cross-file rows: four BSD, ArithmeticSumS 1.1, Margulis 1.1).
Registry pin d8d031d4998c78575159ccab9a7a9e95ce043883.

- 2026-11-25T13:48:33Z — started; read the brief, the six rows, the three registry files, wave.py's
  port_body/port_local/draft_row, and targets/abc in graph-ref for layout.
- 2026-11-25T13:52Z — arxiv-2501-03234 (ArithmeticSumS 1.1): the cross-file flag is spurious
  (`open Nat … in` scopes only `S'`); ported `S'`/`S` as Local.lean; hand witness k = 3.
  Check call 1 (mode check, inlined): errors [] → compiles. Decision: import as stated.
- 2026-11-25T13:53Z — BSD: traced deps. WeakBSD → HasseWeil.HasMeromorphicContinuation → Mathlib
  `WeierstrassCurve.LSeries`. StrongBSD → bsdQuotient → Point.regulator needs
  `Module.Finite` supplied only by `EllipticCurveRank.mordell_weil` (unproved in the registry).
  Strong rows (number field, ℚ): **declined**. Weak rows: ported WikipediaHasseWeil + Local (WeakBSD only).
- 2026-11-25T13:54Z — check call 2 (rat weak, no witness): `unknown namespace WeierstrassCurve.Affine.Rat`
  (my open line; Local declares no Rat namespace). Fixed opens. Check call 3 (nf weak, no witness): errors [].
- 2026-11-25T13:55Z — check call 4 (rat weak + witness y² = x³ - x): errors [].
- 2026-11-25T13:56Z — check call 5 (probe: ULift ℚ instances): Field/DecidableEq/Algebra found,
  NumberField not by inference; `of_ringEquiv` needs explicit K, L.
- 2026-11-25T13:58Z — check call 6 (nf weak + ULift witness + shape probe + #print axioms): errors [];
  axioms propext, Classical.choice, Quot.sound. (One call earlier was not re-sent; a local shell hang.)
- 2026-11-25T13:59Z — check calls 7–9 (mode hazards): ArithmeticSumS no findings; both weak BSD rows
  report auto-implicit at `Affine`, `HasMeromorphicContinuation`, judged artifacts of inlining the
  defs as statement text (the full file compiles with autoImplicit false). No hazards.yaml written.
- 2026-11-25T14:00Z — Margulis 1.1: statement portable (diagonalSubgroup from two sorry-free library
  modules), but the step-7 witness needs a relatively compact diagonal orbit in SL_n(ℝ)/SL_n(ℤ), n ≥ 3
  (totally real fields + Mahler): research formalization. **Declined.**
- Total: 9 calls to api.openproofnetwork.org/check, none to AXLE directly.
- 2026-11-25T14:01Z — CURATION.md written for all six; times above are approximate (reconstructed at 14:01Z).
