# Verdict on hole h4 of the erdos-69 skeleton (69-R3-b, 2026-10-01)

**Verdict: UNKNOWN, leaning sound. Not false on any test I could run, not circular, not the published argument.**
Nothing here is a proof of h4. Admitting the 13 definitions is safe (they cannot make the root wrong); building on h4
is a bet on new mathematics that no expert has read.

## 1. Is it the Tao–Teräväinen argument? No.
Source: arXiv:2512.01739 (Tao, Teräväinen, "Quantitative correlations and some problems on prime factors of consecutive
integers", Theorem 1.3). I could read the introduction and Tao's blog summary; the page text was cut before section 5,
so the comparison is against the method as the authors describe it, not against their formulas.

| | published | 69-R2-b's definitions |
|---|---|---|
| family | alternating sum over a cube {0,1}^K, 2^K terms | product of M hexagons, 6^M terms |
| dilations | primes p (relations along n + ph) | rough numbers 1 + P#(1+g) |
| depth removed | K, growing with n (K about log log log log n) | 3M, fixed |
| what survives | total weight 1, energy 2^-K | total weight (3/4)^M, energy about (6/64)^M |
| large prime factors | weight 1, so the triangle inequality gives only O(1); needs Pilatte's two-point correlation estimate | weight (3/4)^M, so the triangle inequality would be enough |

The drafted definitions do not express the published construction. To express it, `gDigit/sDigit/sign` would be replaced
by a cube family indexed by `Fin K → Bool` with prime dilations, and the decay hole would then contain a Pilatte-type
correlation theorem (far beyond this network's reach today). I do not recommend that change.
Caution: if 69-R2-b's route works it proves the theorem *without* the correlation estimate the authors call essential.
That is possible (the hexagon removes 3 depths with 6 lines where a cube uses 8) but it is exactly the kind of claim
that should be read by a number theorist before thousands of lines are built on it.

## 2. Attack on h4 as stated
- **Cancellation**: re-ran `verify_pattern.py`; exact at all depths ≤ 3M for M ≤ 5 (`coeffs.py`).
- **Re-coincidence beyond depth 3M** (the flagged risk): it happens (14, 94, 996, 6218 points for M = 2..5) but does not
  kill the signal. Surviving energy Σc² = 3.1e-3, 1.7e-3, 2.6e-5, 1.5e-5 for M = 2..5; the model decay exponent
  κ(M,q) = Σ_x (1 − cos 2πq c_x) is positive for every M ≤ 5, q ≤ 12 (0.061 at M=2,q=1; 5.2e-4 at M=4,q=1). Two lines
  meet at one depth only, so far enough down every point is a single line with weight 2^-u and q/2^u is not an integer:
  κ > 0 always. A *quantitative* lower bound on κ is still owed (a lemma, elementary).
- **Exact numerics** (`charmean_M1.py`, exact ω, M = 1, P = 7, the real definitions, numbers up to 2e18):
  |charMean| at T = 4000 is 0.079 for q = 1 and ≤ 0.037 for q = 2..512 (noise floor 0.016); q·signedTail lies within
  0.05 of an integer for 9.8–10.3% of t (uniform: 10%). Standard deviation of signedTail 0.34. No concentration near
  integers, no bad denominator found.
- **No trend can be measured at the parameters h4 needs.** The budget `6^M·5/log P < ε` forces log P > 5·6^M/ε, and
  the decay needs log log z of order 1/κ (about 11^M). Every prime ≤ P contributes exactly zero to signedTail (all lines
  agree mod p and the signs sum to 0), so the decay comes only from primes above P. h4 is true or false at sizes like
  exp(exp(10^40)); numerics can only test the mechanism, which they support.
- **Why I lean sound** (sketch, mine, unchecked): split ω at z = T^δ. Small primes: Kubilius-type model for the
  6^M·O(M) shifts gives |mean| ≤ (log z / log p₀)^(−κ) + sieve error. Large primes: L¹ size ≤ 2πq·(3/4)^M·(log(1/δ)+O(1)),
  using Mertens (node spec-7d098d5c); δ of order 1/(6^M·M) makes this (3/4)^M·O(M) → 0. Fixed parts (primes of the
  dilations) are a constant phase. M must be even or large for the weight to be < 1 (M = 1 leaves depth 3 uncancelled,
  weight 9/8); harmless because M is existential.
- **Circularity**: root ⇒ h4 has no short proof (the family, signs and base point are forced; 69-R1-a's a = 1 trick does
  not apply). h4 ⇒ root needs spec-84446025 and h2, h3 in an essential way. Not circular. No Lean exhibit to file.
- **One weakness in the wording**: M = 0 is allowed (one term, dilation 1 + P#). That instance says the plain tail
  q·Σ ω(m+u)/2^u is not concentrated mod 1, which nobody can prove without the published machinery. It does not make
  h4 false; it means "h4 for some M" should not be attacked at M = 0.

## 3. What I recommend
1. Admit the definitions as drafted. Submit the skeleton, then h1, h2, h3 (all three now proved and fast-checked).
2. Do not leave h4 as one hole. Split it so each risk is a separate statement that can fail on its own:
   h4a exact cancellation; h4b the 2^-3M factorisation; h4c lower bound on κ (the re-coincidence risk);
   h4d large-prime L¹ bound from Mertens; h4e the small-prime model (the big one, a multi-shift fundamental lemma);
   h4f decay of the model product.
3. Before h4e is attempted, put the sketch of section 2 in front of a number theorist (or post it on the erdosproblems.com
   thread for #69): the claim "no correlation estimate needed" is either a real simplification or hides the error.

Files: `coeffs.py`, `charmean_M1.py`, `charmean_M1_T4000.out`, `signedTail_M1_P7.npy`, `H2.lean`, `H3.lean`.
