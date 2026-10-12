"""Complete enumeration (no n cap) of exceptions with n >= k^2 for small k.

Uses the fact proved in Lean on erdos-1094--h1 (Proof.lean): if n >= k^2 and minFac C(n,k) > n/k,
then m = k*(n//k) divides k!, i.e. B = n//k divides (k-1)!.  So every such exception has
n in [k*B, k*B + k - 1] for some divisor B of (k-1)! with B >= k.  For each candidate we test
primes p <= B in increasing order (Lucas digit test for p <= k; n % p < k for p > k) and stop at
the first divisor of C(n,k).  A candidate surviving all sieved primes with B beyond the sieve is
reported as UNRESOLVED (none expected).
"""
import sys, math

KMAX = int(sys.argv[1]) if len(sys.argv) > 1 else 20
PLIM = 2_000_000

def sieve(n):
    b = bytearray([1]) * (n + 1); b[0] = b[1] = 0
    for i in range(2, int(n ** 0.5) + 1):
        if b[i]:
            b[i * i::i] = bytearray(len(b[i * i::i]))
    return [i for i in range(n + 1) if b[i]]

P = sieve(PLIM)

def dom(n, k, p):
    while k:
        if k % p > n % p:
            return False
        k //= p; n //= p
    return True

def factor_fact(m):
    """prime exponents of m! (Legendre)."""
    out = {}
    for p in P:
        if p > m:
            break
        e, q = 0, p
        while q <= m:
            e += m // q; q *= p
        out[p] = e
    return out

def divisors_from(fac):
    ds = [1]
    for p, e in fac.items():
        ds = [d * p ** i for d in ds for i in range(e + 1)]
    return ds

found, unresolved = [], []
for k in range(1, KMAX + 1):
    ds = divisors_from(factor_fact(k - 1))
    cand = 0
    for B in ds:
        if B < k:
            continue
        for n in range(k * B, k * B + k):
            if n < k * k:
                continue
            cand += 1
            if n == 1 and k == 1:
                continue  # n = k = 1: minFac 1 = 1, not > 1
            divides = False
            for p in P:
                if p > B:
                    break
                if (p <= k and not dom(n, k, p)) or (p > k and n % p < k):
                    divides = True
                    break
            else:
                if B > PLIM:
                    unresolved.append((n, k))
                    continue
            if not divides:
                found.append((n, k))
    print(f"k={k}: divisors of (k-1)! = {len(ds)}, candidates n = {cand}", flush=True)
print("exceptions with n >= k^2 (complete, no n cap):", found)
print("unresolved:", unresolved)
