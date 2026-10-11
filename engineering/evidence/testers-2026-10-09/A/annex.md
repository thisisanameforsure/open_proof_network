A parity split of the residue form, and why no elementary range of n falls out of the large primes.

**1. The split.** The statement asks, for all large k and every n with 2k ≤ n < k², for a prime p ≤ k with n mod p < k mod p. The prime p = 2 settles one of the four parity classes outright: when k is odd and n is even, n mod 2 = 0 < 1 = k mod 2, and 2 ≤ k once k > 1. What remains is two classes, each its own statement with its own bound:

- `h_keven`: there is K₁ such that for every k > K₁ with k even and every 2k ≤ n < k², some prime p ≤ k has n mod p < k mod p.
- `h_odd`: there is K₂ such that for every k > K₂ with k odd and every odd n with 2k ≤ n < k², some prime p ≤ k has n mod p < k mod p.

The assembly takes K = max(K₁, K₂, 1) and splits on the parities of k and n. It is proved; only the two classes are open. Neither class alone gives back the statement: each says nothing about the other's pairs, and both are implied by the statement itself, so the split loses nothing and assumes nothing.

**2. Numbers.** A direct scan of every k ≤ 500 and every 2k ≤ n < k² (all primes p ≤ k) finds 301 failing pairs, none with k odd and n even (as the p = 2 argument requires). The even-k failures number 208, the last at (n, k) = (1579, 58); the odd/odd failures number 93, the last at (1469, 39). So numerically K₁ = 58 and K₂ = 39 work up to k = 500. This agrees with the 2026-10-08 scan to k = 1000 recorded on this node (last failure (1579, 58)).

**3. Why I did not split by a range of n instead.** For a prime p in (k/2, k] one has k mod p = k − p, and n mod p < k − p holds exactly when some multiple mp lies in (n − (k − p), n]. For a fixed m that asks for a prime in ((n − k)/(m − 1), n/m], an interval of length (mk − n)/(m(m − 1)) that is empty for n ≥ mk and has ratio of endpoints (m − 1)n / (m(n − k)), which is below 2 whenever n ≥ 2k. So Bertrand's postulate, the only prime-in-interval theorem I could rely on, gives no range of n by itself, and the large primes alone still fail sporadically across the whole range: for k = 75 the failures of the primes in (k/2, k] alone run from n ≈ 12.5k to n ≈ 0.97k², and for k = 150 one failure sits at n ≈ 109k. An elementary range split would need primes in short intervals ((1 + ε)x), which the pinned Mathlib does not carry. The real content of both holes is the equidistribution of n/p modulo 1 over primes (Granville–Ramaré 1996, Konyagin 1999), as the annex on the parent says; I have not checked that those papers prove exactly the last-digit form.

Numerics: a Python sieve over all primes up to k, run by tester t1009-a; script and output in the tester's evidence.
