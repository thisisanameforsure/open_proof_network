Informal argument for the skeleton on the hole left by the size-p / size-(p+1) skeleton of erdos-402--h3-v2 (graph PR #289).

The hole asks for Graham's bound, some a, b in B with gcd(a, b) <= a/|B|, for a finite set B of positive integers with gcd 1, every a <= |B| gcd(a, b), every prime power dividing an element below |B|, and |B| = n neither a prime nor one more than a prime.

The skeleton proves every n <= 44 and leaves one hole: the same statement with n >= 45.

1. n = 1: take a = b.
2. n prime, or n = q + 1 with q prime: excluded by the hypotheses.
3. The other sizes up to 44 are 9, 10, 15, 16, 21, 22, 25, 26, 27, 28, 33, 34, 35, 36, 39, 40. For each, the "largest element" argument already used on erdos-402's variants (spec-fa8046e4, variant-77918742) applies to any set of n positive integers, without the extra hypotheses. Let M be the largest element. If some x has n gcd(M, x) <= M, take a = M, b = x. Otherwise every other x is M j/k with 1 <= j < k < n, and x maps to L j/k with L = lcm(1..n-1), injectively. A finite certificate splits the values L j/k into n - 2 classes in which two distinct members c, d always have n gcd(c, d) <= c or <= d. By pigeonhole two of the n - 1 non-maximal elements x, y land in one class, and gcd(L x/M, L y/M) M = L gcd(x, y) carries n gcd(c, d) <= c back to n gcd(x, y) <= x.

The Lean proves the pigeonhole step once, as a generic lemma over n, L and the class list, and checks each certificate with `decide +kernel`: that k divides L for k < n, that every L j/k lies in a class of index < n - 2, and the class property.

Computational evidence (Python, not Lean): a largest-degree-first greedy colouring of the conflict graph gives such a certificate for every n from 3 to 90 except n = 66, and a tabu search found one for n = 66. So the bound 44 is set by kernel time, not by the mathematics: n = 40 alone takes about 12 s to check. The remaining hole is the Balasubramanian-Soundararajan range, and this route shrinks it but can never close it.
