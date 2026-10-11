# Independent brute force: the largest set containing 1 whose pairwise ratios all have both
# reduced terms <= p + 1 (a Graham counterexample of size p + 2 would be one of size p + 2).
from fractions import Fraction as Fr
from math import gcd
def ok(x, y, m):
    r = x / y; return r.numerator <= m and r.denominator <= m
def omega(m):
    F = sorted({Fr(u, v) for u in range(1, m+1) for v in range(1, m+1) if gcd(u, v) == 1 and Fr(u, v) != 1})
    adj = {x: {y for y in F if y != x and ok(x, y, m)} for x in F}
    best = [0]
    def bk(R, P, X):
        if not P and not X: best[0] = max(best[0], len(R)); return
        u = max(P | X, key=lambda v: len(adj[v] & P))
        for v in list(P - adj[u]):
            bk(R | {v}, P & adj[v], X & adj[v]); P = P - {v}; X = X | {v}
    bk(set(), set(F), set())
    return best[0] + 1
for p in [2, 3, 5, 7, 11, 13]:
    print('p', p, 'n = p+2 =', p + 2, 'largest admissible set', omega(p + 1))
