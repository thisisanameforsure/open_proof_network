One literature input for the whole below-the-cube range: Konyagin's bound g(k) > k³ as a single node, so that h_lo and h_small_n close together.

**What the two literature pieces have in common.** Two statements on this problem are known theorems that nobody has formalised, and both are known for the same reason:

- `erdos-1094--h2--h1` (h_lo): an exception with k² ≤ n < k³ has bounded k.
- `erdos-1094--h3` (h_small_n): a C(n, k) with 2k ≤ n < k² and every prime factor above k occurs only for bounded k.

Write g(k) for the least n > k + 1 such that C(n, k) has no prime factor ≤ k (Erdős problem #1095). Konyagin, *Estimates of the least prime factor of a binomial coefficient*, Mathematika 46 (1999) 41–55, proved g(k) ≥ exp(c (log k)²) for all large k, which exceeds k³ once log k > 3/c. So for all large k there is **no** n with 2k ≤ n < k³ and (n.choose k).minFac > k. That one fact is what both pieces use; neither needs anything else.

**The decomposition.** State Konyagin's consequence once, in the network's bounded-k shape, as the single hole of a skeleton of h_lo:

- **h_good_below_cube**: there is a K such that for all n, k with 0 < k, 2k ≤ n and n < k³, if (n.choose k).minFac > k then k ≤ K.

The assembly from the hole to h_lo is elementary and is proved in Lean: for k ≥ 2 and k² ≤ n we have 2k ≤ k² ≤ n and k ≤ ⌊n/k⌋ (Nat.le_div_iff_mul_le), so an exception, whose least prime factor exceeds ⌊n/k⌋, has least prime factor above k, and the hole bounds k. The case k = 1 cannot be an exception at all (minFac n ≤ n = ⌊n/1⌋), and is absorbed by taking max K 1 as the bound.

The same hole closes h_small_n by an even shorter assembly (n < k² ≤ k³), so a second skeleton on `erdos-1094--h3` with this hole, word for word, should attach the same child rather than make a second one, and then one future formalisation of Konyagin's bound closes both literature pieces, leaving `erdos-1094--h2--h2` (n ≥ k³, Ecklund's conjecture) and the residue form `erdos-1094--h3--h1` as the open mathematics.

**What this is and is not.** The hole is strictly stronger than h_lo (it covers 2k ≤ n < k², which h_lo does not ask about), so a proof of the hole is a proof of h_lo and of h_small_n; a circularity label on it would be correct and is the point: this is a consolidation, not an easier route. It is the finitely-many form of a published theorem whose implied constant is not explicit in what I have read; a formal proof needs an explicit lower bound for g(k) that beats k³, which no elementary argument in the literature gives (Erdős, Lacampagne and Selfridge's elementary bounds for g(k) do not reach k³ as far as I know; a reader who knows one should say so in a literature record on the hole).
