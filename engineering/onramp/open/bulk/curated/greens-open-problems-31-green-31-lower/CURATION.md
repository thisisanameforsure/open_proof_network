# greens-open-problems-31-green-31-lower — curation (curator C)

**Decision: import adapted** (existence form; the lead should confirm, see "For the lead").

Row: `fc:FormalConjectures/GreensOpenProblems/31.lean#green_31.lower`, registry commit
d8d031d4998c78575159ccab9a7a9e95ce043883.

## Exact text change

```
-- registry
theorem green_31.lower :
    -- Break the O(1) barrier
    Filter.Tendsto (fun N ↦ green_31.lower.answer N - Real.sqrt (N : ℝ)) atTop atTop ∧
    ∃ᶠ N in atTop, green_31.lower.answer N ≤ F N
-- graph
theorem Opn.lower :
    ∃ L : ℕ → ℝ,
    -- Break the O(1) barrier
    Filter.Tendsto (fun N ↦ L N - Real.sqrt (N : ℝ)) atTop atTop ∧
    ∃ᶠ N in atTop, L N ≤ F N
```

Checked in Lean: `(∃ a, Reg31lower a) ↔ <graph statement>` is `Iff.rfl`, `Reg31lower` being the
registry body copied verbatim with the answer as a parameter.

## What it says, and why the existence form is honest

The statement is equivalent to `sup_N (F(N) − √N) = ∞`: the largest Sidon subset of `[N]`
exceeds `√N` by an unbounded amount for infinitely many `N`. Green, Problem 31: "Improve, at
least for infinitely many N, the bounds N^{1/2} + O(1) ⩽ F(N) ⩽ N^{1/2} + N^{1/4} + O(1)." The
lower-bound half of that, read as the registry reads it ("Break the O(1) barrier"), is exactly
this statement.

- Open: Green lists it (2024); all known constructions (Singer, Bose, Ruzsa) give Sidon sets of
  `Z/qZ` of size `√q + O(1)`, hence `F(N) ≥ √N + O(1)` and no more (Green's comments).
- Non-trivial: the known lower bound is the `O(1)` it asks to beat.
- No source conjectures it. The direction is the registry's question (F11-Q24 precedent).

## Ports

- `defs/Local.lean`: `F`, `IsGroupSidon`, `IsBinarySidon` copied line for line; removed: module
  syntax, all theorems (conjectures, `category API` lemmas and `category test` examples) with
  their docstrings, and the four placeholder answers.
- `defs/CombinatoricsBasic.lean`, `defs/CombinatoricsAPBasic.lean`: copied unchanged from the live
  graph's `targets/erdos-30/defs/` (`Finset.maxSidonSubsetCard`, `IsSidon`).
- `defs/DataZModFp.lean`: library module `FormalConjecturesForMathlib.Data.ZMod.Fp` ported by
  hand in the driver's form (`𝔽₂`, needed by `IsBinarySidon`).

## Witness

No hypotheses: `theorem witness : True := trivial`.

## Checks

- Compile: `POST /check` 2026-11-25T13:57:45Z, log_id `01M89FZ5SG3Q77DPZEH44168T6`, errors `[]`,
  one `sorry` warning at `Opn.lower`.
- Transcription: combined check 2026-11-25T13:59:30Z, log_id `01M89G2J68W1KRJE47ZSYP2P1Q`, errors
  `[]`.

## For the lead

Related live target: erdos-30 (`F(N) = √N + O(N^ε)` for every ε). This statement is independent
of it in logic (erdos-30 bounds `F` from above). I could not read erdosproblems.com/30 (HTTP 403),
so I cannot confirm whether Erdős stated a belief that `F(N) = √N + O(1)`; if he did, this
statement is the direction opposite to Erdős's belief, still open, and the lead may prefer to
decline it.

## Hazards

None known; no `hazards.yaml`.
