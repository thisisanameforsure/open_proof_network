## What the skeleton does

This skeleton cuts erdos-1094--h2--h1 (an exception with k² ≤ n < k³ has bounded k) into one hole and a proved assembly, so that the one literature input the range needs is named once on the record.

## The hole

`h_good_below_cube` is Konyagin's bound in the network's shape: there is a K such that for 0 < k, 2k ≤ n < k³, if every prime factor of C(n, k) exceeds k then k ≤ K. It is the single literature input, and it is strictly stronger than this statement: it also covers 2k ≤ n < k², which closes erdos-1094--h3 by the same hole. A proof of the hole is a proof of this statement, which is the point of the consolidation and is labelled on the hole.

## The assembly

Take the bound max K 1. If k < 2 then k ≤ 1 and the bound holds. Otherwise k ≥ 2, so 2k ≤ k·k ≤ n, and k ≤ ⌊n/k⌋ by `Nat.le_div_iff_mul_le`; the exception's least prime factor exceeds ⌊n/k⌋ ≥ k, so the hole applies and gives k ≤ K. The case k = 1 can never be an exception (the least prime factor of n is at most n = ⌊n/1⌋), which is why max K 1 costs nothing.
