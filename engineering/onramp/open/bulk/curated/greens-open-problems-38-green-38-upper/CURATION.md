# greens-open-problems-38-green-38-upper — curation (curator C)

**Decision: import adapted.**

Row: `fc:FormalConjectures/GreensOpenProblems/38.lean#green_38.upper`, registry commit
d8d031d4998c78575159ccab9a7a9e95ce043883.

## The driver's second refusal is spurious

"opens another registry file's namespace (Set)": the file's `open Filter Set` opens Mathlib's
`Set` namespace, not a registry file's. The statement uses nothing from another registry file.

## Exact text change

```
-- registry
theorem green_38.upper :
    LargestAdmissibleCardinality ≤ᶠ[atTop] green_38.upper.answer ∧
    ∃ c : ℝ, 0 < c ∧ c < C₂ ∧ green_38.upper.answer =O[atTop] (fun n ↦ c ^ n)
-- graph
theorem Opn.upper :
    ∃ U : ℕ → ℝ,
    LargestAdmissibleCardinality ≤ᶠ[atTop] U ∧
    ∃ c : ℝ, 0 < c ∧ c < C₂ ∧ U =O[atTop] (fun n ↦ c ^ n)
```

Checked in Lean: `(∃ a, Reg38upper a) ↔ <graph statement>` is `Iff.rfl`.

## What it says, and why the existence form is honest

A set `A ⊂ F₇ⁿ` with `(A − A) ∩ {−1,0,1}ⁿ = {0}` is an independent set in the n-th strong power of
the 7-cycle, so `LargestAdmissibleCardinality n = α(C₇^{⊠n})`. The statement is equivalent to
`Θ(C₇) < ϑ(C₇) = C₂`: if `Θ < C₂`, take `U = LargestAdmissibleCardinality`, `c = Θ`, using
`α(C₇^{⊠n}) ≤ Θⁿ` (Fekete, supermultiplicativity); conversely `α ≤ K cⁿ` eventually gives `Θ ≤ c`.
(Argued by hand, not in Lean.)

- Open: Green, Problem 38: "This is a notorious open problem, that of the Shannon capacity of the
  7-cycle … the upper bound C2 = 7 cos(π/7)/(1 + cos(π/7)) ≈ 3.3177 is from Lovász's celebrated
  paper". A search on 2026-11-25 found no improvement of the upper bound; recent work (IRCR26,
  Ga26, BPZ26, all cited in the registry file) moves only the lower bound, now about 3.2588.
- Non-trivial: whether Lovász's bound is tight for odd cycles ≥ 7 is a famous open question.
- No source conjectures the direction; it is the registry's question ("Can we improve the best
  upper bound?"), the F11-Q24 precedent.

## Ports

- `defs/Local.lean`: `IntersectsOnlyAtZero`, `ValidCardinalities`, `LargestAdmissibleCardinality`,
  `C₁`, `C₂`, and `green_38.lower.answer` (a real definition, kept) copied line for line;
  removed: module syntax, theorems and tests with docstrings, and the placeholder
  `green_38.upper.answer`.
- `defs/DataZModFp.lean`: library module `FormalConjecturesForMathlib.Data.ZMod.Fp` (`𝔽₇`), ported
  by hand in the driver's form.

## Witness

No hypotheses: `theorem witness : True := trivial`.

## Checks

- Compile: `POST /check` 2026-11-25T13:58:35Z, log_id `01M89G0JQ0E8RN2VTW9BR2JMRV`, errors `[]`,
  one `sorry` warning at `Opn.upper`.
- Transcription: combined check 2026-11-25T13:59:30Z, log_id `01M89G2J68W1KRJE47ZSYP2P1Q`, errors
  `[]`.

## Hazards

None known; no `hazards.yaml`.
