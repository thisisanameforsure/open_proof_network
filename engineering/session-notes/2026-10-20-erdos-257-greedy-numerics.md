# Erdős 257: the greedy walk to 1/2, numerically (2026-10-20)

Investigation only. Nothing here touched the record or the site. Scripts, raw outputs and the
chart are in `engineering/evidence/erdos-257-greedy-2026-10-20/`.

## Setup

The question (crux `spec-a70fcca4`): is 1/2 an infinite subset sum of 1/(2^a − 1)? Each term
exceeds the sum of all later terms (the gap lemma, `spec-ddd99827`), so a representation is unique
and the greedy walk is the only candidate: at position m, take 1/(2^m − 1) iff it fits under the
remainder. The walk ends in one of three ways: remainder 0 (finite, impossible for an even
denominator), remainder above the tail of the series (stall: 1/2 is not a subset sum), or forever
(1/2 is an infinite subset sum and the root theorem of erdos-257 is false).

The exact-rational walker from 2026-10-19 reaches depth 2500 in two minutes. Today's walker keeps
the carry as an exact integer and the fractional state as 256-bit fixed point with a tracked error
bound, and refuses to decide when the bound straddles the threshold. It reproduces the exact
walker's set and remainders for 1/2, 1/4, 3/8 and 1/16 to depth 2500 (`verify.py`), then runs to
a million in about twenty seconds. No decision was ever ambiguous (no flags) in any run.

## The mechanism, exactly

Write S_m for the partial sum over the elements chosen below m. Since 1/2 = 0.0111… in binary,
the greedy rule is: **m is chosen iff bit m of S_m is 0** (bits 2..m−1 of S_m are already all 1).
Each term 1/(2^a − 1) = 0.(0…01) repeating with period a, so bit m receives a 1 from every chosen
a dividing m, plus the carry from the right:

    bit_m = ( D(m) + carry_in(m) ) mod 2,   D(m) = #{a chosen, a < m : a | m},
    carry_in(m) = floor( D(m+1)/2 + D(m+2)/4 + D(m+3)/8 + … ).

**Correction (same day):** the bit rule is the leading order only. Bit m+1 of S_m is 0 iff
r_m > 2^{−(m+1)}; the term is taken iff r_m ≥ 1/(2^{m+1} − 1), which is slightly larger. In the
sliver between the two (width about 2^{−(2m+2)}) the bit says "take" and the term does not fit;
that sliver is exactly where the stall question lives. In bits, entering it at step m means S_m
reads: ones at 2..m, a zero at m+1, then ones at every position m+2..2m+2. Its upper two-thirds
is the stall; its lower third survives by taking every term for about the next m steps (a run of
about m consecutive chosen elements would be the signature of a near-miss; none was seen, the
longest run at 10^6 is 20). The table below holds for m = 2..40 because the sliver was never hit
(`mechanism_table.txt`). Position 1 is the other exception (its target bit
is 1, and 1/(2^1 − 1) = 1 is too big anyway). The scaled remainder u_m = 2^m r_m is
1 − frac(f_m) with f_m = Σ_j D(m+j) 2^{−j}, and the walk stalls iff a position is *not* chosen
while u_m lies in a window of width 2^{−m}/6 just above 1/2. So the stall probability at step m
is about 2^{−m}/6 under any "random bits" model, and the total after step 7 is below 10^{−3}.

The early elements read off the table: 2, 3 (nothing divides them, no carry); 6 (divisible by 2
and 3, two 1s, bit 0); 7 (prime, carry 0); 14 (2 and 7); 20, 21, 26, 27, 32..35, 38, 39 (one
divisor each, carry 1). The pairs at even starts are just the carry pattern of the first few
elements, not a law: by 40 the parity-conditioned adjacency is gone (below).

## What a million steps show

Everything below is for x = 1/2 unless stated; 1/4, 1/8, 1/16 and 3/8 behave the same way
(their outputs are beside this note). 5/16 stalls at step 5.

**Which a are used.** 501,014 of the first 10^6 integers. First sixty:
2, 3, 6, 7, 14, 20, 21, 26, 27, 32, 33, 34, 35, 38, 39, 42, 44, 45, 46, 47, 48, 49, 50, 51, 53, 55,
56, 57, 58, 59, 60, 63, 65, 66, 70, 74, 75, 82, 86, 87, 89, 91, 93, 96, 98, 99, 100, 102, 103,
104, 107, 108, 113, 122, 123, 125, 126, 130, 133, 135. Non-elements: 1, 4, 5, 8..13, 15..19,
22..25, 28..31, 36, 37, 40, 41, 43, 52, 54, 61, 62, 64, …

**Step sizes.** The gap distribution is geometric with ratio 1/2 to within sampling noise at every
gap from 1 to 15 (ratio observed/expected within 1.00 ± 0.05; 251,101 gaps of 1, 125,236 of 2,
62,446 of 3, …). Mean gap 1.996. Largest gap 23, at a = 299,951, against log2(N) ≈ 20; under
the coin model a gap ≥ 23 among 5·10^5 gaps has probability about 0.11. Runs of consecutive
elements are geometric too (longest 20). The transition matrix of consecutive gaps is the product
of the marginals: the next gap does not depend on the last one.

**Where they sit.** Residues mod 2..8 uniform to three decimals. Primes: 50.3% are elements
(for a prime, D = 0, so this is the carry parity alone). Powers of two in A: 2, 32, 512, 2048,
4096, 65536, 131072, 262144; not: 4, 8, 16, 64, 128, 256, 1024, 8192, 16384, 32768, 524288.
P(2a ∈ A | a ∈ A) = 0.5000, and likewise for 3a..12a; whether a is in A says nothing about its
multiples. Membership does not depend on the number of divisors of m either.

**Randomness tests.** Autocorrelation of the indicator at lags 1..40 is within noise.
Non-overlapping k-bit block chi-square for k = 1..16: p-values between 0.013 and 0.86, no
pattern. The scaled remainder u_m is uniform on [0, 1] (50 bins, all within 1% of flat).

**Discrepancy.** #(A ∩ [1, n]) − n/2 reached 1215 at n ≈ 986,000 and ends at 1014, against a
coin's standard deviation of 500 at n = 10^6: about 2σ. The other four walks end at 94, 504,
−28 and −780; the five together have root-mean-square 616 against 500 expected. Consistent with
a fair-coin random walk; not evidence of a drift.

**The one thing that is not a coin.** Conditioned on the carry c_m into position m (the exact
integer the walker keeps), the probability that m+1 is chosen is far from 1/2:

| c_m | n | P(m+1 ∈ A) |
|---|---|---|
| 1 | 395 | 0.005 |
| 2 | 27,628 | 0.205 |
| 3 | 118,534 | 0.403 |
| 4 | 179,481 | 0.481 |
| 5 | 176,836 | 0.521 |
| 6–12 | 139,888 → 17,166 | 0.536 → 0.549 |
| 13–29 | 12,768 → 326 | 0.52–0.54 |

The same curve appears for 1/4, 1/8, 1/16 and 3/8 (c = 2: 0.22–0.29; c = 3: 0.41–0.44;
c ≥ 6: 0.53–0.55). The parity of D(m+1) adds a small shift (even 0.505, odd 0.497, about 6σ at
this sample size). This is the mechanism showing through, not a lever: the carry is a function of
the past, and the marginal statistics above say the bits it produces are fair.

**Close calls.** Only the first seven steps were ever near a stall. The nearest was m = 6:
u_6 = 32/63 against the threshold 64/127, chosen by a margin of 0.004 (scaled, 0.51 against the
stall ceiling of 1/4 on the other side). Since then no unchosen step has come within a factor of
60 of its window, and the count of near-misses matches the coin model (1, 2, 3 steps within
scaled distance 1, 2, 4 against about 1, 2, 4 expected).

## What this says

- The set A for 1/2 carries no visible arithmetic structure: not in which a are used, not in the
  step sizes, not in residues, primes, powers of two or multiples. Every test at depth 10^6 is
  consistent with independent fair bits, and the carry recursion is the only "formula" there is.
- Under that model the walk's chance of ever stalling was spent at steps 1–7 (it survived one
  genuine close call at m = 6); the remaining probability is below 10^{−3} and halves every step.
  This supports Kovač's expectation that the root theorem is false, and equally says that no
  computation can settle `spec-a70fcca4`: a proof would need a reason the bits never fall in a
  window of width 2^{−m}/6, which is a property of the carry dynamics, not of any finite prefix.
- The useful product is the sliver statement: the walk lives forever iff, for every m with bit
  m+1 of S_m zero, the bits m+2..2m+2 of S_m are not all ones (bar the survivable lower third).
  Nothing known reaches it: the walk's only provable invariants are that r_m has 2-adic valuation
  exactly −1 and that the carry equals ⌈f_m⌉ while alive, and the denominator of S_m (about
  2^{m²/4}) is far too large for Diophantine approximation to exclude the sliver. It is a
  shrinking-target problem for one orbit of a chaotic map, and a proof would need an invariant,
  an algebraic description of A (excluded in every ordinary form above), or a theorem "survival
  to step M implies survival forever". (The 2026-10-19 annex #777 states the carry recursion in a
  different normalisation; the two agree.)
- The 2026-10-19 memory note's idea 1 ("find a formula for A") stays abandoned, now with a reason:
  if there were one, the 16-bit block test or the gap transition matrix would have shown it.

## Reproduce

    cd engineering/evidence/erdos-257-greedy-2026-10-20
    uv venv .venv && uv pip install --python .venv/bin/python numpy scipy matplotlib
    .venv/bin/python verify.py                       # fast vs exact walker, depth 2500 (~10 min)
    .venv/bin/python greedy_fast.py 1 2 1000000 walk_1_2.npz
    .venv/bin/python analyze2.py walk_1_2.npz --plot  # analysis_1_2.txt, walk_1_2.png
    .venv/bin/python extra.py walk_1_2.npz           # parity adjacency, gap transitions, strip
