"""List (n, k) with 0<k, 2k<=n, minFac(C(n,k)) > max(n//k, k), for k<=K, n<=N; classify by A's split."""
import math, sys
def minfac(m):
    if m < 2: return m
    for p in range(2, 10**6):
        if p*p > m: return m
        if m % p == 0: return p
K, N = int(sys.argv[1]), int(sys.argv[2])
for k in range(1, K+1):
    for n in range(2*k, N+1):
        c = math.comb(n, k)
        # only need to know whether a prime <= max(n//k,k) divides c
        b = max(n//k, k)
        if all(c % p for p in range(2, b+1)):
            side = "large (n>=k^2: h_fixed_k/h_large_n)" if k*k <= n else "small (h_small_n)"
            print(n, k, side, "n < k!+k" if n < math.factorial(k)+k else "VIOLATES lemma A")
