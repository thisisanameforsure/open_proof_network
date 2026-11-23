# Hazard pass, lane 3 — 23 targets, all read (2026-11-23)

| target | verdict | checkers | gist |
|---|---|---|---|
| beaver-math-olympiad-problem-1 | acknowledged | nat-sub, nat-sub | both subtractions guarded by the if-branch they sit in |
| collatz-like | acknowledged | off-by-one-range | n > 8 is the stated range; 2^8 is an exception |
| elliott-halberstam | acknowledged | div-zero, off-by-one-range ×3 | x > 2 makes log positive; ranges match docstring exactly |
| erdos-1062 | acknowledged | div-zero | real division by n, zero only at n = 0, limit atTop |
| erdos-1137 | acknowledged | div-zero | primeGap ≥ 1 so sup positive for x ≥ 1 |
| erdos-137 | acknowledged | off-by-one-range | k ≥ 3 is the stated hypothesis, inclusive |
| erdos-249 | acknowledged | div-zero | real division by 2^n, never zero |
| erdos-32 | acknowledged | off-by-one-range | Icc 1 N is {1,…,N} as stated |
| erdos-389 | acknowledged | off-by-one-range ×2 | n ≥ 1 stated; k ≥ 1 excludes vacuous empty product |
| erdos-478 | acknowledged | div-zero ×3, off-by-one-range | limit along primes so p ≥ 2; Ico 1 p is 1 ≤ k < p |
| erdos-566 | acknowledged | nat-sub, off-by-one-range | 2k−3 guarded by k ≥ 2, only meaningful reading |
| erdos-663 | acknowledged | off-by-one-range ×2 | Icc 1 k and k ≥ 2 both verbatim from informal |
| erdos-726 | acknowledged | div-zero ×3, junk-value, off-by-one-range | modulo conjoined with p.Prime; log log n fine eventually; range (n+1) is p ≤ n ("n % a" is the checker's rendering of the lone n % p) |
| erdos-86 | acknowledged | nat-sub | n − 1 under ∀ᶠ n atTop, no truncation for n ≥ 1 |
| erdos-893 | acknowledged | div-zero | f n ≥ τ(1) = 1 for n ≥ 1, zero only at 0 |
| erdos-98 | acknowledged | div-zero | real division by n, zero only at n = 0, limit atTop |
| fermat-number-are-composite | acknowledged | off-by-one-range | n > 4 stated; F_0..F_4 are the known Fermat primes |
| green-64 | acknowledged | nat-sub | p prime so p − 2 never truncates |
| infinitely-many-woodall-primes | acknowledged | nat-sub, off-by-one-range | 1 < k stated; k·2^k ≥ 8 so no truncation |
| lemoine-conjecture | acknowledged | off-by-one-range | odd n > 6 is exactly odd n ≥ 7 |
| pillais-conjecture | acknowledged | nat-sub, off-by-one-range ×4 | c > 0 makes ℕ-subtraction equation equal integer one; exponents > 1 standard (informal says only "positive"; m or n = 1 trivially infinite) |
| rlog-pi-transcendental | acknowledged | junk-value | π > 0 so log π genuine |
| taxicab-for-5-2-n | acknowledged | off-by-one-range | n ≥ 2 verbatim from informal |

Note: locations are copied byte-for-byte from lane-3.json, which carries `↑`/`φ` as literal six-character escapes for ↑/φ in erdos-1062, erdos-1137, erdos-249, erdos-893, erdos-98 (same as other lanes' outputs).
