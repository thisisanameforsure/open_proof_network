The analytic step of Granville–Ramaré's Theorem 8 (§5e, pp. 24–25 of their preprint), split along its own seams: a prime-sum lower bound and the equidistribution bound (5.1).

**Source.** A. Granville and O. Ramaré, Mathematika 43 (1996) 73–107; page numbers are the authors' preprint's. Read by t1015b-g and t1015b-h on 2026-10-15. This node is the hole `h_gr` of the skeleton on erdos-1094--h3 (annex there).

**The statement.** For every C there is K such that for k > K, k² ≤ C·n·log₂k and n < k², some prime p with k/2 < p < 11k/20 has n mod p < k mod p.

**GR's argument (p. 25), and the form used here.** Suppose no such p. For such p, k mod p = k − p, so n mod p ≥ k − p, i.e. the fractional part {n/p} ≥ k/p − 1 > 20/11 − 1 = 9/11. (GR work with m = n − k and get {m/p} < 1/5 for every such p; the condition is the same no-carry condition read from the other summand, and using n avoids natural subtraction. This is our deviation in form, not in substance.) Hence each term ({n/p} − 1/2) log p is at least (7/22) log p, and

Σ_{k/2<p<11k/20} ({n/p} − 1/2) log p ≥ (7/22) Σ_{k/2<p<11k/20} log p.

- `h_cheb` (used, not proved, by GR: the "≫ k" on p. 25): Σ_{k/2<p<11k/20} log p ≥ k/100 for large k. This is the prime number theorem for the interval (x, 1.1x): θ(1.1x) − θ(x) ~ 0.1x with x = k/2, so the sum is ~ k/20. Bertrand's postulate is too weak and Chebyshev's elementary constants do not reach a ratio of 1.1.
- `h_sander` ((5.1), p. 18, the J = 1 case of Lemma 5.1, which GR take from Sander [Sa2], J. reine angew. Math. 430): for every C and ε > 0, for large k on the range above, |Σ_{k/2<p<11k/20} ({n/p} − 1/2) log p| ≤ εk. From (5.1) with x = n and y = k/2, 11k/20: the error terms are y^{3/2+δ}x^{−1/2}log⁵x ≪ k^{1/2+2δ} (as n ≫ k²/log k) and y^{1−c(log y/log x)²}log⁵x ≪ k^{1−c/4+o(1)} (as n < k²), both o(k). GR's ψ is 0 at integers and {t} − 1/2 elsewhere; the two differ only at primes p | n, of which there are at most two in (k/2, k] when n < k² and k > 8, so the difference is O(log k). That is our second deviation in form.

**Assembly (proved in Lean).** With ε = 1/1000: (7/22)(k/100) > k/1000, a contradiction. So the assembly is elementary; both holes are analytic number theory (h_cheb: PNT in short intervals; h_sander: exponential sums over primes, Vaughan's identity).
