# Exploration (Python, exact rationals) for |A| = p + 3: ratio terms <= p + 2.
# Within one residue class (p-free part mod p), which reduced ratios occur, and how large is a clique?
from fractions import Fraction as Fr
from math import gcd
def ok(x, y, m):
    r = x / y; return r.numerator <= m and r.denominator <= m
def cls(x, p):
    a, b = x.numerator, x.denominator
    while a % p == 0: a //= p
    while b % p == 0: b //= p
    return a * pow(b, -1, p) % p
def clique_max(V, m):
    V = list(V); adj = {x: {y for y in V if y != x and ok(x, y, m)} for x in V}
    best = [0]
    def bk(R, P, X):
        if not P and not X: best[0] = max(best[0], R); return
        u = max(P | X, key=lambda v: len(adj[v] & P))
        for v in list(P - adj[u]):
            bk(R + 1, P & adj[v], X & adj[v]); P = P - {v}; X = X | {v}
    bk(0, set(V), set()); return best[0]
for p in [5, 7, 11, 13, 17]:
    m = p + 2
    F = {Fr(u, v) for u in range(1, m + 1) for v in range(1, m + 1) if gcd(u, v) == 1}
    same = {x for x in F if cls(x, p) == 1}
    ratios = sorted({x for x in same if x > 1})
    print('p', p, 'within-class ratios > 1:', [str(r) for r in ratios], 'max within-class clique through 1:', 1 + clique_max({x for x in same if x != 1}, m))
