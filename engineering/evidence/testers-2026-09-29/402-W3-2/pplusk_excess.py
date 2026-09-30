# For |A| = p + k (ratio terms <= p + k - 1): the largest "excess" |S| - (number of residue classes S meets)
# over all compatible sets S (maximal cliques suffice: excess never drops when an element is added).
# A class-counting proof of Graham's bound for p + k needs max excess <= k (then |S| <= (p - 1) + k).
import sys
from fractions import Fraction as Fr
from math import gcd
def ok(x, y, m):
    r = x / y; return r.numerator <= m and r.denominator <= m
def cls(x, p):
    a, b = x.numerator, x.denominator
    while a % p == 0: a //= p
    while b % p == 0: b //= p
    return a * pow(b, -1, p) % p
def max_excess(p, k):
    m = p + k - 1
    F = sorted({Fr(u, v) for u in range(1, m + 1) for v in range(1, m + 1) if gcd(u, v) == 1 and Fr(u, v) != 1})
    adj = {x: {y for y in F if y != x and ok(x, y, m)} for x in F}
    C = {x: cls(x, p) for x in F}; C[Fr(1)] = 1
    best = [(-1, 0, None)]
    def bk(R, P, X):
        if not P and not X:
            S = R + [Fr(1)]
            e = len(S) - len({C[x] for x in S})
            if e > best[0][0]: best[0] = (e, len(S), sorted(S))
            return
        u = max(P | X, key=lambda v: len(adj[v] & P))
        for v in list(P - adj[u]):
            bk(R + [v], P & adj[v], X & adj[v]); P = P - {v}; X = X | {v}
    bk([], set(F), set())
    return best[0]
for k in [2, 3, 4]:
    for p in [3, 5, 7, 11, 13]:
        if p + k > 18: continue
        e, n, S = max_excess(p, k)
        print('k', k, 'p', p, 'max excess', e, 'bound needs <=', k, 'OK' if e <= k else 'FAILS', 'example size', n, [str(x) for x in S])
        sys.stdout.flush()
