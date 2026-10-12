"""Independent check of 'good' pairs: 2k <= n < k^3 and no prime p <= k divides C(n,k),
by direct gcd of C(n,k) with the primorial of k (exact big-integer arithmetic)."""
import math, sys
K = int(sys.argv[1])
out = []
for k in range(1, K + 1):
    prim = math.prod(p for p in range(2, k + 1) if all(p % q for q in range(2, int(p**0.5) + 1)))
    c = math.comb(2 * k, k)
    for n in range(2 * k, k ** 3):
        # C(n,k) updated incrementally: C(n+1,k) = C(n,k)*(n+1)/(n+1-k)
        if math.gcd(c, prim) == 1 and c > 1:
            out.append((n, k))
        c = c * (n + 1) // (n + 1 - k)
for n, k in out:
    print("G", n, k)
