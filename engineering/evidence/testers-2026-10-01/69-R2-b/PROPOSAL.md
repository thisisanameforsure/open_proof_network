# Proposal: admit one definitions file so erdos-69 can be decomposed honestly (69-R2-b, 2026-10-01)

**Ask.** A curator admits `69-R2-b/Defs.lean` as `targets/erdos-69/defs/Construction.lean` (78 lines, 13 definitions, `import Mathlib` only). A contributor then submits `69-R2-b/Skeleton.lean` as a partial on `erdos-69`.

**Provenance.** Clean-room. Written from the mathematics and from the annexes on the record (99dda822, 9445873d, 595b57d6). I did not read, fetch or copy plby/lean-proofs, and could not reach arXiv:2512.01739 (fetch not approved in this session). The cancellation pattern is my own derivation; it should be reviewed as new mathematics, not as a transcription.

**Status of the Lean (fast check only, lean-4.33.1 pin, POST /check mode `check`; nothing seen by the gate).**
- Defs + Skeleton: okay, log_id 01M3VR0MD83CV9GHWVWNNPFHGX. The root's assembly is complete (no `sorry` in `Opn.erdos_69`); the only `sorry`s are the four holes and the two restated proved nodes.
- Defs + SecondLayer: okay, log_id 01M3VR1VF8AQWAZ19MCXTTD5BK (h1 proved; the M = 2 cancellation verified by `decide +kernel` on the actual definitions).

## The definitions and why each is needed
A dilated tail `tail a m = Σ_{u≥1} ω(a(m+u))/2^u` with `a | n+s`, `m = (n+s)/a` reads ω along the line `u ↦ n + s + a·u` with weight `2^-u`. With `a = 1 + P#·(1+g)`, `s = P#·σ`, two lines meet at depth `u` iff `(g−g')u + (σ−σ') = 0`. For depths `u1<u2<u3` with unequal gaps, six signed lines `±β_i(1, −u_i)`, `β = (u3−u2, u1−u3, u2−u1)`, cancel pairwise at all three depths. Triples `{1,2,4},{3,5,6},{7,8,10},{9,11,12},…` cover every depth ≤ 3M with M triples; the product has `6^M` lines and what survives has weight `2^-3M` per line, total mass `(3/4)^M → 0`.

| definition | what it is | why |
|---|---|---|
| `tail a m` | the dilated tail (expression of spec-9f8cb4ea / spec-84446025) | vocabulary for everything else |
| `gDigit r k`, `sDigit r k` | slope and offset digit of line k (of 6) in triple r | the pattern itself; two 6-entry tables |
| `gIndex`, `sIndex`, `sign` | base-7 slope, offset, and ±1 sign of a label `d : Fin M → Fin 6` | the product pattern |
| `dil`, `shift` | `1 + P#(1+g)` and `P#·σ` | rough dilations (fits spec-e0b917d1 exactly) |
| `modulus`, `Admissible`, `start`, `step` | product of dilations; CRT system; the progression of each line | "one progression on which every term is a dilated tail" |
| `signedTail`, `charMean` | the signed combination; mean of `e(q·)` over `t < T` | what the decay theorem is about |

Wrong definitions cannot make the root wrong (the root's statement does not mention them); they can only make a hole false or unprovable.

## Holes (4), and the assembly
The root is proved from h1..h4 plus two proved nodes (spec-84446025, spec-e0b917d1) in about 110 lines: rationality gives `q·x = z`; spec-84446025 puts each `q·tail` near an integer on average, so `‖charMean − 1‖ ≤ 4πqε`; h4 gives `‖charMean‖ < ε`; `1 ≤ ε + 4πqε` fails for `ε = 1/(2+26q)`.

| hole | statement | reach | circular? |
|---|---|---|---|
| h1 | `gIndex M d < 7^M` | **proved** (SecondLayer.lean, 15 lines) | no rationality, no ω |
| h2 | `7^M ≤ P` → prime factors of `dil d` coprime to `step d` | in reach, est. 80–120 lines (gcd of two dilations divides `g−g' < 7^M ≤ P`; needs digit injectivity) | no ω |
| h3 | `7^M ≤ P` → an admissible `n₀ < modulus` exists | in reach, est. 100 lines (`Nat.chineseRemainderOfFinset`; same coprimality as h2) | no ω |
| h4 | ∀ q ≥ 1, ε > 0 ∃ M P T: budgets `< ε` and `‖charMean q M P n₀ T‖ < ε` for every admissible `n₀ < modulus` | **the theorem**; not in reach of one session | see below |

Circularity test on h4 (69-R1-a's trick: a = 1, b = 0, Q = 1, T = 2, free coefficient c, density of multiples of qx): it does not apply. Every dilation is `≥ 1 + P# ≥ 3`, the coefficients are the fixed signs, the family is determined by (M, P), and the base point is forced. The only free choices are M, P, T, and irrationality of x says nothing short about means of `e(qx·Σ ±2^{m_d(t)})` along a prescribed sparse family. I could not derive h4 from the root; I have not tried to get a gate ruling.

Second layer under h4 (statements checked in SecondLayer.lean): h4a exact cancellation at depths `1..3M` (elementary, an involution on labels; checked numerically for M ≤ 4 by `verify_pattern.py` and by kernel evaluation for M = 2); h4b `signedTail = 2^-3M · Σ sign · tail(…, start + step·t + 3M)` (elementary given h4a). Then: large primes contribute at most `(3/4)^M · O(log(log(QT)/log z))` in mean (needs Mertens: 69-R2-a's node spec-7d098d5c); small primes `≤ z` are compared with an independent model by finite moments on the progression; the model's characteristic function decays because Σ 1/p diverges.

## What a curator would have to do
1. Decide that a target's `defs/` may `import Mathlib` (euclid-primes' defs do not) and may hold `noncomputable` definitions.
2. Read the 13 definitions against this page; add `targets/erdos-69/defs/Construction.lean`.
3. Nothing else: no licence question (CC-BY/own work), no third-party notice.

## Honest estimate and risks
- h1–h3 and h4a/h4b: one or two agent sessions, about 500 lines.
- h4 proper: the bulk of the work, several thousand lines of new Lean (R1-b estimated 5–6k for a full clean-room rewrite; this proposal fixes the construction and the assembly, perhaps 10–15% of that).
- **h4 is not proved and I have only a sketch that it is true.** Specific risks: (a) lines may coincide again beyond depth 3M and reduce the variance the decay needs (the numerics show such coincidences exist: weights 3·2^-(3M+1) appear; a lower bound on the surviving non-integer mass is still owed); (b) h4 quantifies T existentially, in a window that depends on M and P; if the proof needs a constraint I did not foresee (e.g. M even), the statement still holds since M is existential; (c) the external proof uses a different pattern (36^m terms), so its lemmas would not port verbatim even with a licence.
- If the owner prefers to wait for a licence on the external proof, its definitions (about 100) would replace these 13; the skeleton shape (construction exists / decay / rational side from spec-84446025) stays the same.
