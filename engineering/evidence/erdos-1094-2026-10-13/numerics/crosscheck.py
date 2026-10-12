"""Brute-force cross-check of the C program on a small box, using math.comb and a direct
least-prime-factor (Mathlib Nat.minFac semantics: minFac 0 = 2, minFac 1 = 1).

Evaluates the root's Lean predicate literally:
  0 < k  and  2*k <= n  and  minFac(C(n,k)) > max(n // k, k)
for k <= KMAX, n <= NMAX, and also reports what happens if the guards are dropped (k = 0, n < 2k).
"""
import math, sys

def minfac(m):
    if m == 1:
        return 1
    if m == 0:
        return 2
    if m % 2 == 0:
        return 2
    p = 3
    while p * p <= m:
        if m % p == 0:
            return p
        p += 2
    return m

def lpf_gt(m, b):
    """True iff minFac(m) > b, without factoring m fully (m >= 2)."""
    if m == 1:
        return 1 > b
    if m == 0:
        return 2 > b
    for p in range(2, b + 1):
        if m % p == 0:
            return False
    return True

KMAX = int(sys.argv[1]) if len(sys.argv) > 1 else 30
NMAX = int(sys.argv[2]) if len(sys.argv) > 2 else 3000
ex = []
for k in range(1, KMAX + 1):
    for n in range(2 * k, NMAX + 1):
        c = math.comb(n, k)
        if lpf_gt(c, max(n // k, k)):
            ex.append((n, k, minfac(c)))
print("root exceptions (literal Lean predicate), k<=%d, n<=%d:" % (KMAX, NMAX), len(ex))
for e in ex:
    print("  C(%d,%d) minFac=%d" % e)

# guards dropped
print("k = 0: C(n,0) = 1, minFac 1 = 1 > max(n/0, 0) = max(0,0) = 0 -> every n would be an exception:",
      minfac(math.comb(5, 0)) > max(5 // 1 * 0, 0))
sym = [(n, n - k) for (n, k, _) in ex]
print("symmetric partners (n, n-k):", sym, "-- excluded by 2*(n-k) <= n unless n = 2k")
nk = [(n, k) for k in range(1, 30) for n in range(k + 1, 2 * k) if lpf_gt(math.comb(n, k), max(n // k, k))]
print("pairs with k < n < 2k satisfying minFac > max(n/k,k) (excluded by the 2k <= n guard), k<30:", len(nk), nk[:20])
