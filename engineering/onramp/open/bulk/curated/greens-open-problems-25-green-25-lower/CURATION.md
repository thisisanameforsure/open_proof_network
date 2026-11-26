# greens-open-problems-25-green-25-lower — curation (curator C)

**Decision: import adapted** (existence form; the lead should confirm, see "For the lead").

Row: `fc:FormalConjectures/GreensOpenProblems/25.lean#green_25.lower`, registry commit
d8d031d4998c78575159ccab9a7a9e95ce043883.

## The registry's statement

`green_25.lower` states three facts about `green_25.lower.answer : ℕ → ℝ := sorry`: it beats the
best-known threshold (`bestLower =o[atTop] answer`, `bestLower N = log log N`), it is a valid
partition size eventually, and every `k ≪ answer` (with `1 ≤ k N ≤ N`) has `Property25` eventually.
The docstring: "We conjecture that the best-known lower bound can be raised."

## Exact text change

`green_25.lower.answer` is replaced by a bound variable:

```
-- registry
theorem green_25.lower :
    (bestLower =o[atTop] green_25.lower.answer) ∧
    (∀ᶠ N in atTop, 1 ≤ green_25.lower.answer N ∧ green_25.lower.answer N ≤ N) ∧
    ∀ k : ℕ → ℕ, ...
      ((fun N => (k N : ℝ)) ≪ green_25.lower.answer) → ...
-- graph
theorem Opn.lower :
    ∃ L : ℕ → ℝ,
    (bestLower =o[atTop] L) ∧
    (∀ᶠ N in atTop, 1 ≤ L N ∧ L N ≤ N) ∧
    ∀ k : ℕ → ℕ, ...
      ((fun N => (k N : ℝ)) ≪ L) → ...
```

Everything else is the registry's text. Checked in Lean: with the registry's body copied verbatim
as `Reg25lower (answer : ℕ → ℝ) : Prop`, `(∃ a, Reg25lower a) ↔ <graph statement>` is `Iff.rfl`.

## Why the existence form is honest here

- No source names a value. Green, Problem 25: "So far as I know, all that is known is the
  following: for k ≪ log log N, this is true, whilst for k ≫ N/ log N, it need not be. These
  results are contained in a 1989 paper of Erdős, Sárközy and Sós [115]." The direction is the
  registry's ("We conjecture that the best-known lower bound can be raised"), the F11-Q24 precedent.
- The existence form says: some threshold growing strictly faster than `log log N` (by more than
  any constant factor) still forces `|⋃ (A_i ∔ A_i)| ≥ N/10`. That is precisely "improve the lower
  bound of [ESS89]", which Green's list (2024) records as not known. It is not trivially true (the
  known result is `k ≪ log log N` with a fixed constant; the registry's own `lower_ess89` is the
  little-o form) and not known false (the failures known are at `k ≥ N^{23/40}`, registry
  `upper_pow_23_40`, far above).
- I could not read erdosproblems.com/484 (HTTP 403 to the fetcher), so I have no confirmation of
  progress after Green's list beyond what the registry file records (which lists none on the lower
  side).

## Ports

- `defs/Local.lean`: `Property25`, `bestLower`, `bestUpper` copied line for line; removed: module
  syntax, theorems with docstrings, and the three placeholder answers (`green_25.answer`,
  `green_25.upper.answer`, `green_25.lower.answer`).
- `defs/CombinatoricsAdditiveRestrictedSumset.lean`: copied unchanged from the live graph's
  `targets/green-2/defs/` (the driver's mechanical port of the library module).
- `defs/AnalysisAsymptoticsBasic.lean`: the library module `FormalConjecturesForMathlib.Analysis.
  Asymptotics.Basic` (the `≪`/`≫` notations), ported by hand in the driver's library-module form.
- A script confirmed every line of each hand port occurs in its source file.

## Witness

No hypotheses: `theorem witness : True := trivial`.

## Checks

- Compile: `POST /check` 2026-11-25T13:57:36Z, log_id `01M89FYT2GEMC1PHR4GNFGM7J1`, errors `[]`,
  one `sorry` warning at `Opn.lower`.
- Transcription: combined check 2026-11-25T13:59:30Z, log_id `01M89G2J68W1KRJE47ZSYP2P1Q`, errors
  `[]` (the `Iff.rfl` above).

## For the lead

The registry's conjecture is its authors' ("We conjecture…"), not Green's; Green only records the
gap. If the network wants a cited source for the direction, this row should be declined instead.

## Hazards

None known; no `hazards.yaml`.
