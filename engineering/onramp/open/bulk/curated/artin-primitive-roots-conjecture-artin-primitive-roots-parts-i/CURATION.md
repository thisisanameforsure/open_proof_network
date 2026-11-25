# wikipedia-artin-primitive-roots-conjecture-artin-primitive-roots-parts-i — curator B, 2026-11-25

**Decision: import as stated.**

Row: `fc:FormalConjectures/Wikipedia/ArtinPrimitiveRootsConjecture.lean#artin_primitive_roots.parts.i`
(registry commit d8d031d4998c78575159ccab9a7a9e95ce043883), `category research open`. Driver
refusals: a cross-file statement (opens `GRH` from FormalConjectures/Millennium/RiemannHypothesis.lean),
binders before the colon carrying hypotheses, and an import the mechanical port cannot supply.

## On GRH (read this first)

This row is the **unconditional** conjecture. Its binders are `(a : ℤ) (ha : ¬IsSquare a) (ha' : a ≠ -1)`, conclusion `∃ x > 0, (S a).HasDensity x {p | p.Prime}` —
there is no GRH or Hooley hypothesis in it, and none was added or removed. The registry states the
conditional form separately as `conditional_artin_primitive_roots.parts.i` (`category research
solved`, with the extra binder `(h : HooleyHypothesis a)`, Hooley 1967), which is not this row.
The statement uses **no name** from the `GRH` namespace: the file's `open GRH` resolves nothing in
either statement. It is kept, unchanged, because the namespace exists once its file's definitions are
ported, and so the statement's text and opens are the registry's.

## Differences from the registry's text

- Theorem name `artin_primitive_roots.parts.i` → `Opn.i` (the driver's `theorem_name` rule:
  `Opn.` plus the last dotted component; the lead may prefer a more telling name, which changes no
  mathematics). Binders and conclusion are the registry's text unchanged.
- Lifted out of `namespace ArtinPrimitiveRootsConjecture`, so `open ArtinPrimitiveRootsConjecture`
  after the file's own `open GRH` and `open scoped Topology Nat`.
- The file's `open Polynomial in` is **not** copied: it scopes only `HooleyHypothesis` in the source,
  never these statements (the driver's regex would copy it as a plain `open Polynomial`).
- Copyright header kept; module syntax replaced by `import Mathlib` + `import Defs.*`.

## Definitions (`defs/`)

- `Local.lean`: from the Artin file, byte for byte, the two definitions the statements use, `S` and
  `ArtinConstant` (source lines 81–90), under the file's header, module doc, `open GRH` and
  `open scoped Topology Nat`. Left out: `IsDedekindZeta`, `DedekindZetaRH`, `HooleyHypothesis`,
  `powCorrectionFactor`, `entanglementFactor` (used only by the file's conditional and power variants;
  `entanglementFactor` would also need `Nat.squarefreePart` from the registry library), the API lemma,
  the conjectures and tests.
- `MillenniumRiemannHypothesis.lean`: RiemannHypothesis.lean's own definitions, i.e. `GRH.trivialZeros`
  (and the empty `RiemannHypothesis` namespace), without its three theorems; the module doc and the
  closing ERH note comment kept. Needed only so `open GRH` resolves.
- `NumberTheoryDirichletCharacterBasic.lean`: the registry library module
  `FormalConjecturesForMathlib/NumberTheory/DirichletCharacter/Basic.lean`, whole (two `DecidablePred`
  instances for `DirichletCharacter.Odd`/`.Even`). Found necessary by the check: without it
  `trivialZeros` fails with `failed to synthesize Decidable χ.Odd`.
- `DataSetDensity.lean` (`Set.HasDensity`) and its four imports `AlgebraOrderGroupPointwiseInterval`,
  `DataSetInterval`, `OrderIntervalFinsetBasic`, `OrderIntervalFinsetNat`: copied unchanged from the
  live graph, where the same five files (same md5 on all 12 targets carrying them) are the driver's
  mechanical port of the registry library at this commit. I diffed DataSetDensity against the source:
  only module syntax and the port note differ.

Every port: `module`, `public import`, `@[expose] public section` removed (the last replaced by
`section`), imports made `import Mathlib` / `import Defs.<Module>`, a port note added; no `sorry`,
`axiom` or `opaque`.

## Witness

`∃ (a : ℤ), ¬IsSquare a ∧ a ≠ -1`, witnessed by a = 2 (if r * r = 2 then |r|·|r| = 2 over ℕ, and |r| ≤ 2 leaves no case).

## Checks

- Inlined file (`import Mathlib`, `autoImplicit`/`relaxedAutoImplicit` false, the seven defs in
  dependency order each in a `section`, statement, witness) sent to `POST /check`, 2026-11-25T13:53Z:
  HTTP 200, `lean_messages.errors == []`, only the statement's `sorry` warning. (First attempt for
  part i, before the DirichletCharacter port, failed on `trivialZeros` as above.)
- Negative control for part ii: the same file with b = 2 in the witness gives an `unsolved goals ⊢ False`
  error on the witness line, so the checker does elaborate the witness.
- `opn_gate.layout.parse_statement` on `Statement.lean`: parses.
- Not run: step-6 hazard checkers. `(p-1 : ℕ)` (natural subtraction) sits inside `S` in defs/, not in the
  statement; at p = 2 it gives 1, the true order bound, so it is no junk value. No hazards.yaml written.
