Elementary constraints on an exception with n ≥ k³ (and in fact with n ≥ k²): what any proof of this hole has to defeat.

Notation: (n, k) is an exception when 0 < k, k² ≤ n and the least prime factor of C(n, k) exceeds B = ⌊n/k⌋. The window is the k integers n − k + 1, …, n, whose product is k! · C(n, k). Every prime of k! is ≤ k ≤ B, and C(n, k) has no prime ≤ B, so the B-smooth part of the window's product is exactly k! (annex 9e0540ba on erdos-1094--h2, §3).

**1. ⌊n/k⌋ divides (k − 1)!.** The window contains m = k·B. Every prime of m is ≤ B, so m is coprime to C(n, k), and m divides k! · C(n, k); hence m | k!, that is B | (k − 1)!. In particular B is never a prime (B ≥ k), and n < k! + k (this is the fixed-k bound proved on erdos-1094--h1). For C(62, 6): B = 10 divides 5! = 120.

**2. A dichotomy for every j with k/2 < j ≤ k.** The window contains t = j·⌊n/j⌋. Each window term is either B-smooth or a prime p > B times a cofactor < k (two primes > B would multiply past n). If c = ⌊n/j⌋ has a prime factor p > B, then t = p · (t/p) with t/p < k, so c/p < k/j < 2 and c = p. Otherwise c is B-smooth, t is B-smooth, and t | k!. So: **for every j in (k/2, k], either ⌊n/j⌋ is a prime greater than ⌊n/k⌋, or j·⌊n/j⌋ divides k!.**

**3. Few B-smooth terms.** Distinct B-smooth window terms are pairwise distinct divisors whose product divides k!, and each is at least n − k + 1. So their number is at most log(k!) / log(n − k + 1). For n ≥ k³ this is about k/3: at least two thirds of the window are a prime > n/k times a cofactor < k, with distinct primes (two multiples of one prime > k cannot both lie in a window of length k).

None of this finishes the hole; it is what a counterexample family would have to satisfy, and it is where a sieve argument (the primes q in (k, n/k] whose multiples the window must avoid) would start. All three facts are short and elementary and could be formalised as `have` steps of a later skeleton.
