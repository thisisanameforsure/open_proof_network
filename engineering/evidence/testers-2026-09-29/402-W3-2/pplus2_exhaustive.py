# Exhaustive check (Python, exact rationals) of the two lemmas behind a proof of Graham's bound
# for |A| = p + 2, p an odd prime.  Scale so one element is 1: every element of a counterexample
# is then a fraction u/v, u, v <= p + 1 (the ratio set F), and every pairwise ratio is in F.
# class(x) = (p-free part of x) mod p, as a residue in 1..p-1 (numerator times inverse of denominator).
from fractions import Fraction as Fr
from math import gcd
import sys
def F_set(m):
    return {Fr(u, v) for u in range(1, m + 1) for v in range(1, m + 1) if gcd(u, v) == 1}
def ok(x, y, m):  # reduced ratio of x and y has both terms <= m
    r = x / y
    return r.numerator <= m and r.denominator <= m
def cls(x, p):
    a, b = x.numerator, x.denominator
    while a % p == 0: a //= p
    while b % p == 0: b //= p
    return a * pow(b, -1, p) % p
def run(p):
    m = p + 1
    F = F_set(m)
    rhos = [Fr(p), Fr(p + 1), Fr(p + 1, p)]
    # Lemma 1: within one class, a clique has at most 3 elements, of the shape g, (p+1)/p g, ... check
    # by enumerating cliques through 1 inside class(1) = 1.
    same = sorted(x for x in F if cls(x, p) == 1 and x != 1)
    best = 1
    for x in same:
        for y in same:
            if y > x and ok(x, y, m):
                best = max(best, 3)
                for z in same:
                    if z > y and ok(x, z, m) and ok(y, z, m): best = max(best, 4)
            elif ok(x, 1, m): best = max(best, 2)
    # Lemma 2: pairs {1, r1} and {y, y r2} (r1, r2 in rhos) with class(y) != class(1): which coexist?
    co = set()
    for r1 in rhos:
        for y in F:
            if cls(y, p) == 1: continue
            for r2 in rhos:
                w = y * r2
                S = [Fr(1), r1, y, w]
                if all(ok(a, b, m) for a in S for b in S):
                    co.add((str(r1), str(r2)))
    return best, co
for p in [3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47]:
    b, co = run(p)
    print(p, 'max clique within a class', b, 'cross-class coexisting pair types', sorted(co))
    sys.stdout.flush()
