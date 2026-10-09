Splitting the open core of Erdős #1094 at n = k³: a literature range and a sharper open range.

**The split.** Call (n, k) an exception when 0 < k, k² ≤ n and the least prime factor of C(n, k) exceeds ⌊n/k⌋. This node asks that every exception have k ≤ K for one constant K. Cut the range of n at k³:

- **h_lo** (k² ≤ n < k³): every exception in this range has bounded k.
- **h_hi** (n ≥ k³): every exception in this range has bounded k.

The assembly takes K = max(K_lo, K_hi) and splits on n < k³; it is proved in Lean. Neither hole implies this node on its own: each is the node restricted to a range, so each is strictly weaker, and both are needed.

**Why h_lo is a literature statement.** For n ≥ k² we have ⌊n/k⌋ ≥ k, so an exception has no prime factor ≤ k: C(n, k) is *good* in the sense of Ecklund, Erdős and Selfridge. So an exception has n ≥ g(k), the least n > k + 1 with C(n, k) good. Konyagin (Mathematika 46 (1999) 41–55) proved g(k) ≥ exp(c (log k)²) for large k, and exp(c (log k)²) > k³ as soon as log k > 3/c. So for all large k there is no exception with n < k³ at all, and h_lo holds with K the largest k below that point. (Granville and Ramaré's earlier bound g(k) ≥ exp(c √(log³k / log log k)) also exceeds k³ for large k, so either reference suffices.) The constant c is not explicit in what I have read, so h_lo is a literature theorem, not yet an elementary Lean proof; a formal proof needs an explicit lower bound for g(k) beating k³. The one known exception, C(62, 6) (k = 6, 36 ≤ 62 < 216), lies in this range, which is consistent: K_lo ≥ 6.

**Why h_hi is the sharper open problem.** h_hi is Ecklund's conjecture in finitely-many form restricted to n ≥ k³, i.e. ⌊n/k⌋ ≥ k². Here the window n − k + 1, …, n must avoid every multiple of every prime q with k < q ≤ n/k, a range containing all primes up to k², and the heuristic in the annex on this node (avoidance probability about (log k / log(n/k))^k) is far smaller there than near n = k². It remains open; no unconditional bound is known to me. The fixed-k bound n < k! + k (proved on erdos-1094--h1) caps its range from above.

**Numerics.** A Kummer-carry scan of every 1 ≤ k ≤ 60 and k² ≤ n ≤ 60000 finds exactly one exception, (62, 6), in the h_lo range, and none with n ≥ k³ (n = k = 1 is not an exception in Lean, since Nat.minFac 1 = 1).
