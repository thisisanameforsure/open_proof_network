# Annex material for erdos-1094--h3 / erdos-1094--h3--h1 (from A, for C to file)

The skeleton merged as PR #448 on erdos-1094--h3 reduces the small-n half of Erdős #1094 to a pure
statement about residues. Nothing about binomial coefficients is left in the hole.

Reduction (proved in the assembly): Lucas's theorem gives
C(n,k) ≡ C(n mod p, k mod p) · C(n div p, k div p) (mod p) for a prime p (Mathlib
`Choose.choose_modEq_choose_mod_mul_choose_div_nat`). If n mod p < k mod p, the first factor is 0, so
p divides C(n,k), and then minFac C(n,k) ≤ p. So if every large k and every n with 2k ≤ n < k² have a
prime p ≤ k with n mod p < k mod p, the exceptions with n < k² have bounded k, which is --h3.

The hole --h3--h1 (h_sieve):
∃ K, ∀ n k, K < k → 2k ≤ n → n < k² → ∃ prime p ≤ k with n mod p < k mod p.
Equivalently: {n/p} < {k/p} for some prime p ≤ k. That is the last base-p digit of the Kummer/Lucas
carry condition.

Status, honestly stated:
- This is STRONGER than --h3, because carries in higher digits are ignored. It is the form a sieve over
  the fractional parts {n/p} attacks. Whether Granville–Ramaré (1996) or Konyagin (1999) prove exactly
  this form (all primes p ≤ k, last digit only, the whole range 2k ≤ n < k²) has NOT been checked against
  the papers.
- Numerics (A/h3b_scan.py, every k ≤ 300 and every n in [2k, k²)): the n where no prime p ≤ k has
  n mod p < k mod p are listed in full there. The last one is (n,k) = (1579, 58); there are none for
  59 ≤ k ≤ 300. So the hole is consistent with K = 58 on that range. Every true exception with n < k²
  (ELS's 13: (7,3), (13,4), (14,4), (23,5), (44,8), (46,10), (47,10), (74,10), (94,10), (95,10),
  (47,11), (241,16), (284,28)) is among those n, as it must be.
- Warning for anyone tempted to do the same for --h2 (n ≥ k², bound n/k): the residue-only form
  fails for small k on infinite-looking families (k=2: n = 2^m and Fermat primes; A/h2_scan.py), so
  it was not proposed.
