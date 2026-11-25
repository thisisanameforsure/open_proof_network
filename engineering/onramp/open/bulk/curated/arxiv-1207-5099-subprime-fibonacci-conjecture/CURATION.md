# arxiv-1207-5099-subprime-fibonacci-conjecture — curator B, 2026-11-25

**Decision: import as stated.**

Row: `fc:FormalConjectures/Arxiv/1207.5099/SubprimeFibonacci.lean#conjecture` (registry commit
d8d031d4998c78575159ccab9a7a9e95ce043883). Driver refusal: binders before the colon carry
hypotheses (`hx : 0 < x`, `hy : 0 < y`), so the witness had to be written by hand.

## Differences from the registry's text

- Theorem name `conjecture` → `Opn.conjecture` (the driver's `theorem_name` rule: `Opn.` plus the
  last dotted component). The binders `(x y : ℕ) (hx : 0 < x) (hy : 0 < y)` and the conclusion
  `EventuallyPeriodic (x, y)` are the registry's text unchanged; the line is broken after the colon
  as the driver writes every statement.
- The statement is lifted out of `namespace Arxiv.«1207.5099»`, so it opens that namespace
  (`open Arxiv.«1207.5099»`), as the driver does for an enclosing namespace.
- Copyright header kept; module syntax replaced by `import Mathlib` + `import Defs.Local`.

## Definitions (`defs/Local.lean`)

The file's own three definitions, `subprimePart`, `step`, `EventuallyPeriodic`, copied byte for
byte (lines 41–58 of the source) under the source's header and module doc, with `module`,
`public import FormalConjecturesUtil` and `@[expose] public section` removed (the last replaced by
`section`, as the mechanical port does). The API lemma and the `category test` theorems are left
out, as the mechanical port leaves them out. No `sorry`, `axiom` or `opaque`.

## Witness

`∃ (x : ℕ) (y : ℕ), 0 < x ∧ 0 < y`, witnessed by x = y = 1.

## Checks

- Inlined file (`import Mathlib`, `autoImplicit`/`relaxedAutoImplicit` false, defs in a `section`,
  statement, witness) sent to `POST https://api.openproofnetwork.org/check` at 2026-11-25T13:52Z:
  HTTP 200, `lean_messages.errors == []`, the only warning the statement's `sorry`.
- `opn_gate.layout.parse_statement` on `Statement.lean`: parses as a `Statement`.
- Not run: the step-6 hazard checkers (no hazards.yaml written; none known).
