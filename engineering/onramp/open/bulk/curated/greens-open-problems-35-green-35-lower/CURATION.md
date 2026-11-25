# greens-open-problems-35-green-35-lower — curation (curator C)

**Decision: declined** — the honest existence form is already known to be true.

Row: `fc:FormalConjectures/GreensOpenProblems/35.lean#green_35.lower`, registry commit
d8d031d4998c78575159ccab9a7a9e95ce043883.

## Why

`green_35.lower` asks for `green_35.lower.answer : ℝ≥0∞ → ℝ≥0∞ := sorry` with
`answer p ≤ c p` for all `p > 1`, and `√(4/7) < answer 2 ∨ 0.64 < answer ∞`. With no value named,
the only import would be `∃ answer, …`, which is equivalent to `√(4/7) < c 2 ∨ 0.64 < c ∞`
(take `answer = c`). Its first disjunct is a published theorem:

- E. P. White, "An optimal L² autoconvolution inequality", Canad. Math. Bull. (2024),
  arXiv:2210.16437 (abstract read 2026-11-25): for `f : [-1/2, 1/2] → ℝ` with `∫ f = 1` (the abstract
  does not say nonnegative; a lower bound over that class holds a fortiori for the nonnegative
  densities of Green's Problem 35, up to translation), it determines `inf ‖f ∗ f‖₂` "up to a 0.0014%
  error … making progress on a problem asked by Ben Green", with published bounds
  `0.574636066 ≤ μ₂² ≤ 0.574642912` (via the search summary of the CMB version). So
  `c 2 ≥ √0.574636 ≈ 0.75805 > √(4/7) ≈ 0.75593`. Rechnitzer (arXiv:2602.07292, 2026) sharpens the
  same constant further.
- Green's list itself still quotes `c₂ ≥ 0.7559…` (= √(4/7)) and the registry's docstring
  ("improving the known value √(4/7) at p = 2") predates or misses White's result.
- The reduction from that bound to the registry's existence form is checked in Lean (combined
  check 2026-11-25T13:59:30Z, log_id `01M89G2J68W1KRJE47ZSYP2P1Q`, errors `[]`): an `example`
  taking `ENNReal.ofReal (√(4/7)) < c 2` as a hypothesis proves `∃ answer, …` by
  `⟨c, fun _ _ => le_rfl, Or.inl h⟩`. White's inequality itself is not formalised.

Translation invariance: `[−1/2, 1/2]` and `[0, 1]` differ by a shift, which leaves `‖f ∗ f‖₂` and
`∫ f` unchanged, so White's constant is the registry's `c 2` (registry: `eLpNorm (f ⋆ f) 2`, the
unsquared norm; White's `μ₂²` is the squared one, hence the square root above).

## What a mathematician would need to decide

Whether a sharper open question exists to import, e.g. `0.64 < c ∞` alone (the `p = ∞` lower
bound of Cloninger–Steinerberger). A search on 2026-11-25 found one 2026 note claiming "a
strengthened autoconvolution inequality" (arXiv:2605.05193) whose constant I could not read, so I
could not certify that the `p = ∞` half is still open, and splitting the registry's disjunction
would be my choice, not the registry's. Not imported.

## Sources read

Registry file 35.lean in full; Green, *100 open problems*, Problem 35 and comments; White's
abstract; search results for later work on both constants.
