# greens-open-problems-31-green-31-upper — curation (curator C)

**Decision: import adapted.**

Row: `fc:FormalConjectures/GreensOpenProblems/31.lean#green_31.upper`, registry commit
d8d031d4998c78575159ccab9a7a9e95ce043883. Shares its registry file and its ports with
greens-open-problems-31-green-31-lower.

## Exact text change

```
-- registry
theorem green_31.upper :
    (∃ᶠ N in atTop, F N ≤ green_31.upper.answer N) ∧
    ∃ c < (0.94349 : ℝ), ∃ C : ℝ, ∀ᶠ N in atTop, green_31.upper.answer N - Real.sqrt (N : ℝ) ≤ c *
      (N : ℝ) ^ (4⁻¹ : ℝ) + C
-- graph
theorem Opn.upper :
    ∃ U : ℕ → ℝ,
    (∃ᶠ N in atTop, F N ≤ U N) ∧
    ∃ c < (0.94349 : ℝ), ∃ C : ℝ, ∀ᶠ N in atTop, U N - Real.sqrt (N : ℝ) ≤ c *
      (N : ℝ) ^ (4⁻¹ : ℝ) + C
```

Checked in Lean: `(∃ a, Reg31upper a) ↔ <graph statement>` is `Iff.rfl`.

## What it says, and why the existence form is honest

Equivalent to: for some `c < 0.94349` and `C`, `F(N) ≤ √N + c N^{1/4} + C` for infinitely many
`N`, i.e. the [HZ26] upper bound improved at least for infinitely many `N` (Green: "Improve, at
least for infinitely many N, the bounds …").

- Open: the best bound is Hou–Zhao [HZ26] (arXiv:2607.01169), `N^{1/2} + γ₀ N^{1/4} + O(1)` with
  `γ₀ = 0.94349… < 0.9435`, valid for all `N`; nothing better is known along any subsequence. A
  search on 2026-11-25 found no later improvement.
- Conjectured: Erdős's conjecture `F(N) = √N + O_ε(N^ε)` for every `ε > 0` (Erdős problem 30,
  live on the graph as erdos-30, "Is it true that, for every ε > 0, h(N) = √N + O_ε(N^ε)")
  implies it: with `ε = 1/8`, `F(N) ≤ √N + K N^{1/8} ≤ √N + ½ N^{1/4}` eventually. So this is a
  weakening of a stated conjecture, in its direction.
- Non-trivial: no improvement of `γ₀` is known even for infinitely many `N`.

## Ports

Identical to greens-open-problems-31-green-31-lower (`defs/Local.lean` byte-identical; same
library ports). See that folder's CURATION.md.

## Witness

No hypotheses: `theorem witness : True := trivial`.

## Checks

- Compile: `POST /check` 2026-11-25T13:57:50Z, log_id `01M89G0HQRFY54S8QBA0PG6QD5`, errors `[]`,
  one `sorry` warning at `Opn.upper`.
- Transcription: combined check 2026-11-25T13:59:30Z, log_id `01M89G2J68W1KRJE47ZSYP2P1Q`, errors
  `[]`.

## For the lead

`0.94349` is the registry's literal. `c` ranges over all reals below it (negative included), as in
the registry; this adds no loophole, since a smaller `c` is a stronger conclusion. The
erdos-30 implication was argued by hand, not checked in Lean.

## Hazards

None known; no `hazards.yaml`.
