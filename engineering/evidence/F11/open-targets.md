# F11-T5 — the five listed open targets: the fact pass, the choice, and the hand QA pass (R13)

2026-09-12. The Stage 0 list is five open problems the network exists for, shown on the Targets
page as *listed, not claimable* (F11-R9, R10; Stages). This is the record R13 asks for before
any of them is listed: how they were chosen from the registry, and the D-9 v3.12 pass run by
hand on each statement — the soundness screens, the back-translation comparison, the licence
check, and the external attempts counted against the statement they ran on.

**Status:** proposed by the fact pass and staged on the graph branch `intake/open-targets`
(commit `9fe468e`, one `intake import-fc` per target, admission deferred to the pull request's
gate). **Mike approves the five by merging that pull request (F11-Q3).** Until then nothing is
listed.

## The fact pass (Q3)

The pass is `docs/seed_conjecture_sources.html` (2026-09-08): every Erdős problem with a Lean
statement in google-deepmind/formal-conjectures at `c7f31d5fd3d2ca3d69979f2d213eb9b58fe956ae`,
joined with erdosproblems.com, the AI-contributions wiki, Epoch's FrontierMath Erdős selections,
AlphaProof Nexus's attempts and the registry's misformalization issues, each row graded A–D by a
recorded trust score. This task committed the join as data —
`docs/seed_conjecture_sources.json`, 640 problems, extracted from the report's §9 by
`docs/seed_conjecture_sources_extract.py` (F11-Q23) — and filtered it:

| filter | rule | left |
|---|---|---|
| open | site status OPEN | 335 |
| trusted | trust grade A or B, no misformalization issue ever filed | 96 |
| in scope | AMS area not in D-6's excluded set (algebraic geometry, algebraic number theory, differential geometry, PDE) | 96 |
| statable | the registry file uses Mathlib names only — no `FormalConjecturesForMathlib` helper, no file-local definition — so the statement imports as one file over the graph's own Mathlib pin | 23 → checked by hand on the trust-A rows |

Trust A alone gives 23 problems. Of those, the ones read for this pass and set aside:

- **#3** (Erdős–Turán, $500), **#371** (largest prime factor, density ½): use `Set.IsAPOfLength`,
  `Nat.maxPrimeFac`, `Set.HasDensity` — the registry's own helpers (`FormalConjecturesForMathlib/`),
  which would have to be ported into `defs/` and QA'd as definitions first. Good second-wave
  candidates once a target may carry ported definitions with certificates of their own.
- **#241** (Bose–Chowla, $500), **#213** (integer distances, no four concyclic): file-local
  definitions (`f`, `Erdos213For`, `NonTrilinear`, `ℝ²`) — the same porting cost.
- **#208** (squarefree gaps, two parts with a local `s`), **#89** (distinct distances, `≫`),
  **#812** (Ramsey ratio): asymptotic notation or a registry helper; the hazard the report's §5
  names for open statements.
- **#324** (polynomial with distinct pair-sums) and **#952** (Gaussian primes with bounded
  steps): clean, Mathlib-only, trust A — the two alternates if any of the five is refused.

The five, and why each (Erdős problems in included domains with an existing Lean statement
preferred, Q3; a spread of areas; a statement a reader can check by hand):

| target | problem | area | since | why |
|---|---|---|---|---|
| erdos-68 | Is ∑ 1/(n!−1) irrational? | number theory | 1968 | one line over `Irrational` and `tsum`; the registry's textbook lemma shows the natural route |
| erdos-376 | infinitely many n with C(2n,n) coprime to 105? | number theory | 1975 | the two-prime case is a theorem [EGRS75]; 105 is the first open case; `Nat.centralBinom` |
| erdos-406 | finitely many powers of 2 with only digits 0,1 in base 3? | number theory | 1979 | `Nat.digits` and `isPowerOfTwo`; attempted twice by Nexus |
| erdos-172 | monochromatic sums and products in any finite colouring | combinatorics | 1977 | a Ramsey-type statement over `Finset` and `Fin n`; Moreira's two-element case is known |
| erdos-52 | the sum-product conjecture, |A+A| or |A·A| ≥ |A|^(2−ε) | number theory, combinatorics | 1977 | Erdős–Szemerédi, $500; pointwise `Finset ℤ`; an AI attempt on a *variant* is on record (June 2026) |

## The adaptation (Q24)

The registry states each as a yes/no question, `answer(sorry) ↔ P`, and its own docstring says
providing the answer "requires evaluation of mathematical meaning, which is a job for human
mathematicians". D-3 wants a proposition, so each target states P — the affirmative reading —
under `import Mathlib`, with the upstream Apache-2.0 header kept byte for byte (R9, AC12) and
the adaptation named in the file. A refutation is D-12's counterexample artifact, so nothing is
lost by stating the affirmative. The informal statement is not reproduced (erdosproblems.com
states no licence; R10): the network's paraphrase stands in its place.

## The hand QA pass, per statement (R13; D-9 v3.12)

Each block: the Lean statement's back-translation and its comparison with the problem as the
site states it (from the joined dataset); the soundness screens (no vacuous hypothesis, a
non-trivial conclusion, no `sorry` outside the statement's own body); the licence; the external
attempts counted, with the hash of the registry file they are attributed to and the hash of the
statement as listed here. AlphaProof Nexus's attempts (Feb 2026) ran against the registry at a
commit the dataset does not record; the count is therefore "attempts on this problem's registry
statement", and the hashes below are the identity the network lists, not a claim about which
bytes Nexus saw.

### erdos-68 — erdosproblems.com/68

- **Lean, back-translated:** The value of the series ∑_{n≥0} 1/((n+2)! − 1), i.e. ∑_{n≥2} 1/(n!−1), is irrational.
- **Comparison with the problem as stated:** Matches the site's question. Reindexing n+2 ↔ n≥2 is exact; the cast `((n + 2).factorial - 1 : ℝ)` subtracts in ℝ after casting, so no truncated subtraction; every term is positive and the series converges (bounded by ∑ 2/n!), so `tsum` is the sum and not the junk value 0. No hypothesis; conclusion is a substantive `Irrational`.
- **Soundness screens:** hypotheses satisfiable — none; conclusion non-trivial — yes; the only `sorry` is the statement's body; the header is the registry's, byte for byte.
- **Licence:** Apache-2.0 (google-deepmind/formal-conjectures); attribution written to the graph's `THIRD_PARTY_NOTICES.md`; the erdosproblems.com wording is cited by link and paraphrased, not reproduced.
- **External attempts counted:** 1 (AlphaProof Nexus, Feb 2026, not solved; the registry's benchmark column reads: FME, FC-reviewed attempted (1), unsolved).
- **Registry file at the pin:** sha256 `ae87fc60cac529122b9a08cbae11df1c98889461372368a3a1b508b84bff11aa` (`FormalConjectures/ErdosProblems/68.lean` at `c7f31d5f…`).
- **Statement as listed:** sha256 `abc6fbf1e2ebedbce8bba7d0e497cffd34ffff17ef3138faeb76b6a6e5be17be`; grade `mechanical-only`, one certificate by the curator; claimable: false (not posted, not signed by a non-author).

### erdos-376 — erdosproblems.com/376

- **Lean, back-translated:** The set of natural numbers n whose central binomial coefficient is coprime to 105 is infinite.
- **Comparison with the problem as stated:** Matches the site. `Nat.centralBinom n = C(2n, n)`; `Nat.Coprime` is gcd 1; `Set.Infinite` is the literal reading of 'infinitely many'. No hypothesis. The registry's solved variant (any two odd primes) is not imported: one statement per target (D-3).
- **Soundness screens:** hypotheses satisfiable — none; conclusion non-trivial — yes; the only `sorry` is the statement's body; the header is the registry's, byte for byte.
- **Licence:** Apache-2.0 (google-deepmind/formal-conjectures); attribution written to the graph's `THIRD_PARTY_NOTICES.md`; the erdosproblems.com wording is cited by link and paraphrased, not reproduced.
- **External attempts counted:** 1 (AlphaProof Nexus, Feb 2026, not solved; the registry's benchmark column reads: FME, FC-reviewed attempted (1), unsolved).
- **Registry file at the pin:** sha256 `57831e75a8569ac441332db76b41282ac4278ee01761a21d65b1d4e3ddb033d6` (`FormalConjectures/ErdosProblems/376.lean` at `c7f31d5f…`).
- **Statement as listed:** sha256 `eaebe54dfc2dc163d73390cf5ae874858b9368062ca1b1719313a4aee8016e15`; grade `mechanical-only`, one certificate by the curator; claimable: false (not posted, not signed by a non-author).

### erdos-406 — erdosproblems.com/406

- **Lean, back-translated:** The set of n that are powers of two and whose base-3 digit list is contained in [0, 1] is finite.
- **Comparison with the problem as stated:** Matches the site's 'only finitely many'. `Nat.digits 3 n` is the little-endian digit list; `⊆ [0, 1]` on lists is membership-wise, so 'only the digits 0 and 1'. `Nat.isPowerOfTwo` includes 1 = 2^0 (base-3 digits [1]), which the site's 'powers of 2' also includes. No hypothesis; finiteness is the substantive claim. The digits-1-and-2 variant stays upstream.
- **Soundness screens:** hypotheses satisfiable — none; conclusion non-trivial — yes; the only `sorry` is the statement's body; the header is the registry's, byte for byte.
- **Licence:** Apache-2.0 (google-deepmind/formal-conjectures); attribution written to the graph's `THIRD_PARTY_NOTICES.md`; the erdosproblems.com wording is cited by link and paraphrased, not reproduced.
- **External attempts counted:** 2 (AlphaProof Nexus, Feb 2026, not solved; the registry's benchmark column reads: FME, FC-reviewed attempted (2), unsolved).
- **Registry file at the pin:** sha256 `3e8dca1a60ce9c1245957f507b32db4c71a9b9b3f88a277a601aaaee9ade82d5` (`FormalConjectures/ErdosProblems/406.lean` at `c7f31d5f…`).
- **Statement as listed:** sha256 `7f09b5c2e133a3a26615bddfb59f2319d55ab6ea14187ad269e5ac4597f39f2b`; grade `mechanical-only`, one certificate by the curator; claimable: false (not posted, not signed by a non-author).

### erdos-172 — erdosproblems.com/172

- **Lean, back-translated:** For every finite colouring c : ℕ → Fin n and every m there is a finite set A of naturals with at least m elements and a colour such that every nonempty subset S of A has both its sum and its product of that colour.
- **Comparison with the problem as stated:** The site says 'all sums and products of distinct elements in A are the same colour'; the Lean quantifies over nonempty `Finset A` (subsets of A), whose sums and products are exactly sums and products of distinct elements — including singletons, whose sum and product is the element itself, so A is monochromatic too, which the site's reading also requires. `A.card ≥ m` is 'arbitrarily large'. `Fin n` with n = 0 makes `color` uninhabited only when ℕ → Fin 0 has no functions, so the ∀ over colourings is vacuous at n = 0 and substantive for every n ≥ 1: not a vacuity, a degenerate case. No `sorry` beyond the body.
- **Soundness screens:** hypotheses satisfiable — yes (see above); conclusion non-trivial — yes; the only `sorry` is the statement's body; the header is the registry's, byte for byte.
- **Licence:** Apache-2.0 (google-deepmind/formal-conjectures); attribution written to the graph's `THIRD_PARTY_NOTICES.md`; the erdosproblems.com wording is cited by link and paraphrased, not reproduced.
- **External attempts counted:** 1 (AlphaProof Nexus, Feb 2026, not solved; the registry's benchmark column reads: FME, FC-reviewed attempted (1), unsolved).
- **Registry file at the pin:** sha256 `905597d193a1134e1a69cc5ae5a8e1eebab015cc010414131faa82a5e74ffde0` (`FormalConjectures/ErdosProblems/172.lean` at `c7f31d5f…`).
- **Statement as listed:** sha256 `11fefc9ebfa3421acccdbf63d4edeaf9b2f7653855cfe15364d05fb91f8d60cd`; grade `mechanical-only`, one certificate by the curator; claimable: false (not posted, not signed by a non-author).

### erdos-52 — erdosproblems.com/52

- **Lean, back-translated:** For every ε with 0 < ε < 1 there is C > 0 such that for every finite set A of integers, max(|A+A|, |A·A|) ≥ C · |A|^(2−ε).
- **Comparison with the problem as stated:** Matches the site's ≫_ε |A|^(2−ε) (the constant depends on ε: C is chosen after ε). `A + A` and `A * A` are the pointwise sumset and product set of a `Finset ℤ` (`open scoped Pointwise`, kept from the registry file). ε < 1 is the registry's restriction, harmless (the case ε ≥ 1 is trivial). The empty set gives 0 ≥ C·0 — true — so no vacuity from A = ∅. The AI-wiki entry is a solution to a variant, not to this statement; it counts as an attempt on the problem, not a resolution.
- **Soundness screens:** hypotheses satisfiable — yes (see above); conclusion non-trivial — yes; the only `sorry` is the statement's body; the header is the registry's, byte for byte.
- **Licence:** Apache-2.0 (google-deepmind/formal-conjectures); attribution written to the graph's `THIRD_PARTY_NOTICES.md`; the erdosproblems.com wording is cited by link and paraphrased, not reproduced.
- **External attempts counted:** 1 (AlphaProof Nexus, Feb 2026, not solved; the registry's benchmark column reads: FME, FC-reviewed; Bloom top 10 attempted (1), unsolved); plus one AI solution to a variant on the AI-contributions wiki (Claude Mythos, 3 June 2026), not to this statement.
- **Registry file at the pin:** sha256 `522ee685d7bc964d45011a725c6b670da2b573fbd9326c6a8a776a09398d8cf6` (`FormalConjectures/ErdosProblems/52.lean` at `c7f31d5f…`).
- **Statement as listed:** sha256 `6c899a4a782f461229c26c4596583a7566632f2937dc1939534eb24d24d3c69f`; grade `mechanical-only`, one certificate by the curator; claimable: false (not posted, not signed by a non-author).

## What this record does not do

It is a hand pass by one person, the curator. D-9 v3.12's second rung wants a non-author's
signature on each statement and F12 wants the mechanizable half of this pass automated; both
are for later. The five are listed to make the mission visible (Stages), and none of them can
be claimed until that happens (F11-R4).
