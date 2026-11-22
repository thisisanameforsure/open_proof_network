# Lane B — witnesses for six refused wave-7 drafts (2026-11-22)

Checker: `witness_check.py` (hosted `POST /check`, mode `witness`, 20 s budget). Witness files in
`$S/overrides/<id>/Witness.lean`. Raw checker JSON beside this file (`dummy-*.json`, `a1-*.json`,
`min-*.json`, `min2-*.json`).

Two defects outside the witnesses dominate this lane, both in the mechanical port of the registry's
shared library (`defs/`), which the driver copies whole into every draft whose file imports it:

- **FieldTheoryMilnorKTheory.lean does not elaborate at the pin** (`Unknown identifier of_mul`, two
  `unsolved goals` at its lines ~256/257 or ~309/310 in the composed file). It is carried by
  erdos-509, erdos-61, erdos-883 and gyarfas-sumner-conjecture, none of whose statements use it.
- **ComputabilityBitstringEncoding.lean does not elaborate** (`simp made no progress` twice, `Unknown
  identifier undelimitBlocks_flatten_delimit`). Carried by gyarfas-sumner-conjecture and erdos-883.

With all of a row's defs inlined the checker answers `okay: false` for the defs' errors even when the
witness itself compiles and `matches: true`. For the diagnosis I copied each such row into
`$S/minimal/<id>/` keeping only the module the statement actually uses (`Local.lean`, plus
`CombinatoricsSimpleGraphCircumference.lean` for erdos-883); against that copy every witness is
**ACCEPTED**. The drafts themselves are untouched. The fix is the port's (drop unused library
modules, or repair the two files), not the witnesses'.

## erdos-383

- Expected: `∃ (k : ℕ), True`
- Attempts: 1 — **ACCEPTED** (against the draft as it stands).
- Witness: `⟨0, trivial⟩`. The driver refused a plain `∀ k` as "untyped"; the binder is a bare ℕ and
  the witness is the trivial closure. (Driver mis-refusal of the cheap kind: an untyped binder whose
  type Lean infers.)

## erdos-985

- Expected: `∃ (p : ℕ), Nat.Prime p ∧ p ≠ (2 : ℕ)`
- Attempts: 1 — **ACCEPTED** (against the draft as it stands).
- Witness: `⟨3, Nat.prime_three, by norm_num⟩`. The `∀ᵉ` binder notation is what the driver could
  not read.

## erdos-509

- Expected: `∃ (f : ℂ[X]), f.Monic ∧ f.natDegree ≠ (0 : ℕ)`
- Attempts: 1 with full defs — `matches: true`, `okay: false`, errors only in
  FieldTheoryMilnorKTheory (`of_mul`); 1 against the Local-only copy — **ACCEPTED**.
- Witness: `⟨Polynomial.X, Polynomial.monic_X, by simp⟩`.
- Verdict on the draft as shipped: NOT ACCEPTED, port defect (unused library module fails to
  elaborate). The witness is right.

## erdos-61

- Expected: `∃ (α : Type u_1) (inst : Fintype α) (inst : DecidableEq α) (H : SimpleGraph α), True`
- Attempts: 1 with full defs — `matches: true`, `okay: false`, same MilnorKTheory errors; 1 against the
  Local-only copy — **ACCEPTED**.
- Witness: `⟨ULift (Fin 1), inferInstance, inferInstance, ⊥, trivial⟩` (the `Type u_1` universe is
  auto-bound in the theorem signature; `ULift` lands the one-vertex type in it).
- Verdict on the draft as shipped: NOT ACCEPTED, port defect. The witness is right.

## erdos-883

- Expected (only readable on a repaired copy):
  `∃ (n : ℕ) (A : Finset ℕ) (l : ℕ), A ⊆ Finset.Icc 1 n ∧ n / 2 + n / 3 - n / 6 < A.card ∧ Odd l ∧ 3 ≤ l ∧ l ≤ n / 3 + 1`
- Attempts: 2 dummy runs with full defs — both `check-timeout` (nine ported modules do not elaborate
  inside 20 s; a checker limit, and the MilnorKTheory/BitstringEncoding errors would follow). Then a
  Local-only copy: the **statement itself fails** — `Unknown identifier coprimeGraph.induce`. Cause:
  the draft's preamble is `open scoped Classical in` / `open Erdos883`, and `in` scopes the Classical
  opening to the *next command*, which is the `open Erdos883` itself, so the namespace is never open
  for the theorem. (Registry file presumably had the `in` directly before the theorem; the driver's
  reordering of `open` lines broke it.) **Statement defect**, independent of the witness. With the
  line changed to `open scoped Classical` on a copy (`$S/minimal/erdos-883b`, plus the circumference
  module for `oddCycleLengths`): 1 dummy to read the type, 1 witness attempt — **ACCEPTED**.
- Witness: `⟨6, Finset.Icc 1 6, 3, Finset.Subset.refl _, by simp, ⟨1, rfl⟩, by norm_num, by norm_num⟩`
  (six elements beat 3 + 2 − 1 = 4; l = 3 ≤ 6/3 + 1).
- Verdict on the draft as shipped: NOT ACCEPTED — checker timeout on the full defs, and under that a
  statement defect (`open … in`). Both are the driver's; the witness is right once they are fixed.

## gyarfas-sumner-conjecture

- Expected: `∃ (W : Type) (inst : Fintype W) (inst : DecidableEq W) (T : SimpleGraph W) (inst : DecidableRel T.Adj), T.IsTree`
- Attempts: 1 with full defs — `matches: true`, `okay: false`, errors only in
  ComputabilityBitstringEncoding; 1 against the Local-only copy — **ACCEPTED**.
- Witness: the one-vertex graph `⊥ : SimpleGraph (Fin 1)`, proved a tree through
  `SimpleGraph.isTree_iff_connected_and_card` (connected by `Subsingleton.elim`, edge count by `simp`).
- Verdict on the draft as shipped: NOT ACCEPTED, port defect. The witness is right.

## Summary

| id | accepted (draft as shipped) | accepted (statement's own defs only) | attempts | note |
|---|---|---|---|---|
| erdos-383 | yes | — | 1 | `⟨0, trivial⟩`; driver mis-refused an untyped `∀ k` |
| erdos-509 | no | yes | 2 | witness right; port defect: unused `FieldTheoryMilnorKTheory` fails (`of_mul`) |
| erdos-61 | no | yes | 2 | witness right (`ULift (Fin 1)`, `⊥`); same MilnorKTheory port defect |
| erdos-883 | no | yes (on a repaired copy) | 4 | full defs time out at 20 s; statement defect `open scoped Classical in` swallows `open Erdos883`; witness n=6, A=Icc 1 6, l=3 |
| erdos-985 | yes | — | 1 | `⟨3, Nat.prime_three, by norm_num⟩`; driver could not read `∀ᵉ` |
| gyarfas-sumner-conjecture | no | yes | 2 | witness right (one-vertex tree); port defect: unused `ComputabilityBitstringEncoding` fails |
