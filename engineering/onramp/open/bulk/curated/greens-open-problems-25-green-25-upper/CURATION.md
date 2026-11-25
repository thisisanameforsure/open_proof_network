# greens-open-problems-25-green-25-upper — curation (curator C)

**Decision: declined** — the honest existence form is already a theorem.

Row: `fc:FormalConjectures/GreensOpenProblems/25.lean#green_25.upper`, registry commit
d8d031d4998c78575159ccab9a7a9e95ce043883.

## Why

`green_25.upper` asks for `green_25.upper.answer : ℕ → ℕ := sorry` with `1 ≤ answer N ≤ N`
eventually, `answer = o(N / log N)`, and `¬ ∀ᶠ N, Property25 (answer N) N`. The answer-shaped
question ("lower the upper bound N/log N") has no stated value, so the only import would be the
existence form `∃ answer, …`. That form is settled:

- The same registry file states `green_25.variants.upper_pow_23_40` (category `research solved`,
  with a linked Lean proof, KitaKen1/green-25-upper-bound): for `k N = ⌈N^{23/40}⌉`, `1 ≤ k N ≤ N`
  eventually, `k = o(N / log N)`, and `∀ᶠ N, ¬ Property25 (k N) N`.
- That implies the existence form, because "eventually not P" contradicts "eventually P" along
  `atTop` on ℕ. Checked in Lean (combined check 2026-11-25T13:59:30Z, log_id
  `01M89G2J68W1KRJE47ZSYP2P1Q`, errors `[]`): an `example` taking `upper_pow_23_40`'s statement as
  a hypothesis proves `∃ answer : ℕ → ℕ, …` (registry text with the answer bound) in four lines.
- Green's own comment already pointed this way: Ruzsa [Ru04] gives partitions with `k = N/m`
  parts and union `O_m(N^{1/2})`.

Importing it would put a known theorem on the frontier as open work, which the brief forbids.
The registry still tags `green_25.upper` `research open`; the registry file itself shows that tag
is stale for the existential reading.

## What a mathematician would need to decide

Whether there is a meaningful *open* upper-side question left (for example the true threshold
exponent, between `log log N` and `N^{23/40}`). That needs a stated conjecture, which no source
read here gives.

## Sources read

Registry file 25.lean in full; Green, *100 open problems*, Problem 25 and comments.
