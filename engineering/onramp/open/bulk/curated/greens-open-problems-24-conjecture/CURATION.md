# greens-open-problems-24-conjecture — curation (curator C)

**Decision: import as stated.**

Row: `fc:FormalConjectures/GreensOpenProblems/24.lean#conjecture` (registry declaration
`Green24.variants.conjecture`), registry commit d8d031d4998c78575159ccab9a7a9e95ce043883.

## Why the driver refused, and why the refusal does not reach this statement

The driver refused the row because the file defines `green_24.answer : ℕ → ℕ := sorry`. That
answer belongs to the question-shaped theorem `green_24` (`∀ n, max013AffineTranslates n =
green_24.answer n`). The row's own declaration, `variants.conjecture : gamma = 1/3`, does not use
any answer: it is a closed proposition about the file's definitions `max013AffineTranslates` and
`variants.gamma`. So nothing has to be adapted; the port simply leaves the placeholder answer out.

## Is it open, and is it a conjecture of a source?

- Green, *100 open problems*, Problem 24 (the PDF read 2026-11-25): "It seems likely that the
  answer is ( 1/3 + o(1))n^2, but this is not known. Aaronson's paper [2] should be consulted for
  more information."
- The registry's docstring cites Aaronson [Aa19] p.579 for the same conjecture,
  `(1/3 + o(1)) n^2`.
- The registry marks it `research open`.

Meaning check (by hand): `max013AffineTranslates n` counts ordered pairs `(x, y)` of distinct
elements of `A` with `x + 3(y - x) ∈ A`, i.e. the affine images `a + d·{0,1,3}` with `d ≠ 0`
(both signs of `d`). The interval `[n]` gives about `n²/6` for each sign, `n²/3` in all, so the
limit inferior of `max/n²` is at least `1/3` and `gamma = limsup max/n² = 1/3` is exactly
"the interval is asymptotically extremal", which is Green's and Aaronson's `(1/3 + o(1))n²`.

## Differences from the registry's text

- Theorem name `Green24.variants.conjecture` → `Opn.conjecture` (the driver's `theorem_name`
  rule); `open Green24` and `open Green24.variants` added so `gamma` resolves as it does inside
  the registry's namespace. The proposition `gamma = 1/3` is byte for byte the registry's.
- `defs/Local.lean`: the file's definitions (`max013AffineTranslates`, `variants.gamma`) copied
  line for line; removed: the module syntax, every theorem and its docstring, and
  `def green_24.answer : ℕ → ℕ := sorry` (a placeholder, forbidden in a definition, and used by no
  imported statement). A script confirmed every line of the port occurs in the registry file.

## Witness

No hypotheses, so `theorem witness : True := trivial`.

## Checks

- `POST https://api.openproofnetwork.org/check`, 2026-11-25T13:57:24Z, log_id
  `01M89FYDC8D5A9BS7RVBN7ZJYG`: `result.lean_messages.errors == []`; one warning, `declaration uses
  sorry`, at `Opn.conjecture` (expected). The file inlined `Local` in its own section, under
  `set_option autoImplicit false` and `relaxedAutoImplicit false`.

## Hazards

None known; no `hazards.yaml`.
