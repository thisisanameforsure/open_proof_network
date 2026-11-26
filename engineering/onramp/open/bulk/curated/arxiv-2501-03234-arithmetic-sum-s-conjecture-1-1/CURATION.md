# arxiv-2501-03234-arithmetic-sum-s-conjecture-1-1 — import as stated

Row: `fc:FormalConjectures/Arxiv/2501.03234/ArithmeticSumS.lean#conjecture_1_1` at registry commit
d8d031d4998c78575159ccab9a7a9e95ce043883. Curator A, 2026-11-25.

## Decision: import as stated

The driver's "cross-file" flag came from `open Nat Finset BigOperators in`, which appears in the file
only as a prefix of the definition `S'`. It names `Nat`, a namespace some registry file also extends.
The statement uses no registry declaration outside its own file: it uses `S` (this file), `Nat.Prime`
and `Odd` (Mathlib). Nothing crosses files. The other refusal, hypotheses before the colon, is met by
the hand witness.

## Differences from the registry's text
- `theorem conjecture_1_1` is `theorem Opn.conjecture_1_1`, lifted out of `namespace Arxiv.«2501.03234»`.
  The statement opens that namespace instead (`open Arxiv.«2501.03234»`) so that `S` resolves as it
  does in the registry. Binders and proposition are byte for byte, with one line break added before
  the conclusion.
- The `open Nat Finset BigOperators in` prefix is **not** opened for the statement: in the registry it
  scopes only `S'`, so the theorem never sees it. The driver would have opened it plainly; that would
  be a scope the registry's theorem does not have.
- `defs/Local.lean`: the file's two definitions `S'` and `S`, byte for byte with their docstrings, the
  comment line and the `open … in` prefix. Their `section SumS` and namespace lines are kept, and the
  module doc and copyright header are kept. Removed: `module`, `public import FormalConjecturesUtil`
  (it becomes `import Mathlib`; `S'`/`S` use Mathlib only), `@[expose] public section` (it becomes
  `section`), the test `S_fst_10` and the five conjectures and four implication tests. No `sorry`,
  `axiom` or `opaque`.
- Witness: `∃ (k : ℕ), k.Prime ∧ Odd k`, the shape `gate/lean/OpnGate/WitnessType.lean` builds (data
  binder `k`, the hypotheses `hprim` and `hodd` conjoined), with k = 3.

## Checks
- `POST https://api.openproofnetwork.org/check` (mode check). Sent: `import Mathlib`, the
  `autoImplicit`/`relaxedAutoImplicit` options off, Local's body in a section, the statement and the
  witness. Result: `lean_messages.errors == []`; the only warning is the statement's `sorry`.
- `POST /check` (mode hazards, the same text up to the witness, as `statement`). Checkers
  auto-implicit, div-zero, int-trunc, junk-value, nat-sub, off-by-one-range and unused-binder:
  **no findings**, so no `hazards.yaml`.

## Sources read
`FormalConjectures/Arxiv/2501.03234/ArithmeticSumS.lean`; `gate/tools/wave.py` (port_body, port_local,
draft_row); `targets/abc` in the graph reference; `gate/lean/OpnGate/WitnessType.lean`.
