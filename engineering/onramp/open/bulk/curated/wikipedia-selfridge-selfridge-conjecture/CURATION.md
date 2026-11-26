# wikipedia-selfridge-selfridge-conjecture — curator B, 2026-11-25

**Decision: import as stated.**

Row: `fc:FormalConjectures/Wikipedia/Selfridge.lean#selfridge_conjecture` (the PSW / Selfridge
primality-test conjecture; not the Sierpiński-number Selfridge conjecture already imported).
Registry commit d8d031d4998c78575159ccab9a7a9e95ce043883. Driver refusal: binders before the colon
carry a hypothesis (`hp : IsSelfridge p`), so the witness had to be written by hand.

## Differences from the registry's text

- Theorem name `selfridge_conjecture` → `Opn.selfridge_conjecture` (driver rule). Binders
  `(p : ℕ) (hp : IsSelfridge p)` and conclusion `p.Prime` unchanged; line broken after the colon.
- Lifted out of `namespace Selfridge`, so `open Selfridge`.
- Copyright header kept; module syntax replaced by `import Mathlib` + `import Defs.*`.

## Definitions (`defs/`)

Copied unchanged from the live target `selfridge-seq-conjecture` (graph reference), which carries
the driver's mechanical port of this same registry file at the same commit: `Local.lean`
(`IsSelfridge`, `IsPseudoSelfridge`, `fermatFactors`) and the four library modules it imports
(`AlgebraWeylAlgebra`, `AnalysisSpecialFunctionsAdditiveCharacter`, `FieldTheoryMilnorKTheory`,
`GroupTheoryRationalClasses`). Re-using the live port keeps one text of `IsSelfridge` on the graph.
I compared `IsSelfridge` in `Local.lean` against the registry: identical in every declaration line; `diff` against the source shows only the module syntax,
the port note, the left-out conjectures and tests, and one blank line the mechanical port drops
inside each structure's doc comment (whitespace in a comment, nothing elaborated).

## Witness

`∃ (p : ℕ), Selfridge.IsSelfridge p`, witnessed by p = 3: odd; 3 ≡ 3 (mod 5); 2² = 4 ≡ 1 (mod 3);
F₄ = 3 ≡ 0 (mod 3). Each field by `decide` (the last `decide +kernel`; no `native_decide`).

## Checks

- Inlined file sent to `POST /check` at 2026-11-25T13:53Z: HTTP 200, `errors == []`, only the
  statement's `sorry` warning.
- `layout.parse_statement`: parses.

## For the lead

`engineering/onramp/open/bulk/overrides/selfridge-conjecture/Witness.lean` already exists with
`⟨3, by decide⟩` for `IsSelfridge p`; I did not check whether `decide` can decide the structure
as a whole (it is a `structure`, not a `Decidable` proposition) and wrote the four fields
separately instead. If that override is meant for this row, prefer this file.
