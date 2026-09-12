# F11-T1 — the on-ramp target, selected against R7

The Stage 0 invited run needs one real target whose whole pipeline — claim, precheck, submit,
merge, root closes — can run in an evening. F11-R7 fixes the criteria; F11-Q1 fixed the kind
(a classic textbook theorem, chosen by Mike on 2026-09-07 for zero selection risk) and named two
starting candidates. This is the record R7 asks for: the choice, its definitions, the planned
lemma structure, each criterion with its evidence, and two rejected alternatives with why.

The machine-readable half of this file is its heading structure: `gate/tests/test_intake.py`
`::test_selection_record_complete` (F11-AC8) reads the criterion and alternative headings back
and fails if one is missing or has no evidence line.

## Chosen

- **theorem:** Euclid's theorem — for every `n` there is a prime greater than `n`.
- **target id:** `euclid-primes`
- **track:** formalization
- **root statement:** `theorem infinitude_of_primes : ∀ n : Nat, ∃ p : Nat, n < p ∧ IsPrime p`
- **domain tags:** `number-theory`, `elementary` — neither is in D-6's excluded set.
- **source:** Euclid, *Elements* IX.20; the argument as it is usually written today is saved
  verbatim as the annex at `gate/tests/fixtures/onramp/annex.md` (D-31), and the skeleton
  submitted in F11-T4 cites it.

## Definitions

Three, all in the graph's own `defs/` (R7's cap is three). None is imported, so no Mathlib
lemma is stated about any of them and no citation closes a node in one line.

| Definition | Shape |
|---|---|
| `Divides a b` | `∃ c : Nat, b = a * c` — written out rather than `Nat.dvd`, so Mathlib's `Nat.dvd` API does not apply to it definitionally by name. |
| `IsPrime p` | `2 ≤ p ∧ ∀ d : Nat, Divides d p → d = 1 ∨ d = p` |
| `fact n` | `fact 0 = 1`, `fact (n+1) = (n+1) * fact n` |

## Lemma structure

Five nodes — four lemmas and the root — which is inside R7's three-to-six band. Each is an
hour's work at most for a competent agent with Mathlib's `Nat` tactics available beneath the
local definitions.

| Node | Statement | Depends on |
|---|---|---|
| `fact-pos` | `∀ n, 0 < fact n` | — |
| `dvd-fact` | `∀ n k, 0 < k → k ≤ n → Divides k (fact n)` | — |
| `prime-divisor` | `∀ m, 2 ≤ m → ∃ p, IsPrime p ∧ Divides p m` | — |
| `dvd-consecutive` | `∀ d m, Divides d m → Divides d (m + 1) → d = 1` | — |
| `infinitude-of-primes` (root) | `∀ n, ∃ p, n < p ∧ IsPrime p` | the four above |

The root's assembly: put `m = fact n + 1`. `fact-pos` gives `2 ≤ m`, so `prime-divisor` gives a
prime `p` with `Divides p m`. If `p ≤ n` then `dvd-fact` gives `Divides p (fact n)` (a prime is
positive), and `dvd-consecutive` forces `p = 1`, contradicting `2 ≤ p`. So `n < p`.

`prime-divisor` is the only lemma with real content (strong induction on `m`); the other three
are the kind of exercise that proves the pipeline rather than the mathematics, which is what an
invited run is for (Stages, v3.11).

## Criteria

Each of R7's six criteria, with the evidence for it.

### elementary-in-an-included-domain

evidence: the argument is Euclid's and needs no machinery beyond `Nat` induction; the domain
tags are `number-theory` and `elementary`, and D-6's excluded set is
{algebraic-geometry, algebraic-number-theory, differential-geometry, pde}. Intake's own
exclusion check (F11-R2, AC2) is what enforces this at seeding time.

### objects-defined-in-the-graphs-own-defs

evidence: all three definitions above live in `targets/euclid-primes/defs/`. Mathlib states
`Nat.exists_infinite_primes` about `Nat.Prime`, not about this `IsPrime`; closing the root from
it would first need `IsPrime p ↔ Nat.Prime p`, which is a proof, not a citation. The same holds
for `Divides` against `Dvd.dvd` — the bridge is a lemma, and proving it is as much work as the
node it would shortcut.

### statable-in-under-40-lines

evidence: the root statement is one line; the three definitions and their imports come to
roughly twenty lines of `defs/`, well under R7's forty. The exact files land in F11-T4 and the
layout check measures them there.

### at-most-three-definitions

evidence: exactly three — `Divides`, `IsPrime`, `fact`. A fourth was considered (`Prime`'s
positivity as a definition rather than a lemma) and folded into `IsPrime` instead.

### decomposable-into-three-to-six-lemmas

evidence: the table above is four lemmas plus the root, each stated independently of the others'
proofs, so they can be claimed in parallel. None needs a construction longer than a dozen lines.

### mathlib-still-pinned

evidence: `gate-spec.json` for this target pins a Mathlib SHA (D-7), so provers may use
`omega`, `induction`, `Nat.le_of_lt_succ` and the rest beneath the local definitions. The pin is
what makes F11-T3's per-graph image necessary; it is not dropped to make the target local.

## Rejected alternatives

Two, as R7 requires.

### sqrt-two-is-irrational

why rejected: it was F11-Q1's other candidate — "no natural numbers p, q with q ≠ 0 and
p² = 2q²" over a local parity definition, with descent in three lemmas. Two problems. The
statement is pure `Nat` arithmetic with no local object in it at all, so it fails the criterion
that matters most here: Mathlib's parity API (`Nat.even_mul`, `Nat.even_pow`) applies to it
directly and closes two of the three lemmas near-instantly, whichever way the local `Even` is
spelled. And the descent gives a three-node graph with one interior lemma, which is the bottom of
R7's band — too thin to exercise the frontier, parallel claiming, or a variant proposal during
the run.

### euclidean-algorithm-computes-the-gcd

why rejected: attractive because it decomposes cleanly, but `Nat.gcd` is in Lean's core, so a
local `gcd` is a near-copy of it and the core lemmas transfer with a `rfl`-shaped bridge —
the same one-line-citation problem, one level down. Worse, a local well-founded recursion makes
the *statement* carry a termination argument, which pushes past R7's forty lines and puts
`decreasing_by` plumbing in front of every prover before any mathematics starts. The invited run
should fail on mathematics or on the protocol, never on recursion syntax.
