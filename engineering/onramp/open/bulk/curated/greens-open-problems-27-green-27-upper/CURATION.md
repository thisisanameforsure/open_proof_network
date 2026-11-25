# greens-open-problems-27-green-27-upper — curation (curator C)

**Decision: import adapted** (existence form; the lead should confirm, see "For the lead").

Row: `fc:FormalConjectures/GreensOpenProblems/27.lean#green_27.upper`, registry commit
d8d031d4998c78575159ccab9a7a9e95ce043883.

## Exact text change

```
-- registry
theorem green_27.upper :
    (green_27.upper.answer =o[primesAtTop] upperBest) ∧ (m =O[primesAtTop] green_27.upper.answer)
-- graph
theorem Opn.upper :
    ∃ U : ℕ → ℝ,
    (U =o[primesAtTop] upperBest) ∧ (m =O[primesAtTop] U)
```

Checked in Lean: with the registry body copied verbatim as `Reg27upper (answer : ℕ → ℝ)`,
`(∃ a, Reg27upper a) ↔ <graph statement>` is `Iff.rfl`.

## What it says, and why the existence form is honest

`∃ U, U = o((log p)²) ∧ m = O(U)` is equivalent to `m(p) = o((log p)²)` along the primes (take
`U = m` one way; compose `O` and `o` the other). So the statement says Bedert's upper bound
`m(p) ≪ (log p)²` [Be23, Theorem 5] is not of the true order.

- Open: Hou and Yang [HY26] (arXiv:2610.09349, abstract read 2026-11-25) prove
  `m(p) ≥ 2^{-80} (log p / log log p)²` and an upper bound with leading term
  `(log p)² / (2 (log 3)²)`, and say "Consequently m(p) = (log p)^{2+o(1)}" and "The
  constant-factor order of m(p) remains undetermined." The registry's own docstring on
  `green_27.lower` agrees: "The exact order of m(p) remains open." Between `(log p/log log p)²` and
  `(log p)²`, `m = o((log p)²)` is neither known nor refuted.
- Non-trivial: it decides the gap above in one direction.
- No source states a conjectured value. Green, Problem 27 (update 2023) records only Bedert's
  bounds. The direction is the registry's ("Propose a better upper bound along primes"), the
  F11-Q24 precedent.

## Ports

- `defs/Local.lean`: `m`, `primesAtTop`, `lowerBest`, `upperBest`, and `green_27.lower.answer`
  (a real definition, `fun p ↦ Real.log p * Real.log (Real.log p)`, kept because the port keeps
  the file's definitions) copied line for line; removed: module syntax, theorems with docstrings,
  and the placeholders `green_27.equivalent.answer` and `green_27.upper.answer`.
- `defs/CombinatoricsBasic.lean`, `defs/CombinatoricsAPBasic.lean`: copied unchanged from the
  live graph's `targets/erdos-30/defs/` (the driver's port; `HasNoUniqueRepresentation`).

## Witness

No hypotheses: `theorem witness : True := trivial`.

## Checks

- Compile: `POST /check` 2026-11-25T13:57:38Z, log_id `01M89FZ0X8BWCNTEJW6TT2YQ07`, errors `[]`,
  one `sorry` warning at `Opn.upper`.
- Transcription: combined check 2026-11-25T13:59:30Z, log_id `01M89G2J68W1KRJE47ZSYP2P1Q`, errors
  `[]`.

## For the lead

The opposite direction (`m(p) ≍ (log p)²`) is equally open and nobody I read conjectures either.
Importing the `o` side follows the registry's question, not a mathematician's conjecture; decline
if the network wants a cited direction.

## Hazards

None known; no `hazards.yaml`.
