# k = 3 (|A| = p + 3, ratio terms <= p + 2): which same-class pair types coexist across two different classes?
from fractions import Fraction as Fr
from math import gcd
def ok(x, y, m):
    r = x / y; return r.numerator <= m and r.denominator <= m
def cls(x, p):
    a, b = x.numerator, x.denominator
    while a % p == 0: a //= p
    while b % p == 0: b //= p
    return a * pow(b, -1, p) % p
for p in [5, 7, 11, 13, 17, 19, 23, 29, 31]:
    m = p + 2
    F = {Fr(u, v) for u in range(1, m + 1) for v in range(1, m + 1) if gcd(u, v) == 1}
    T = {'A': Fr(p + 1), 'B': Fr(p + 2, 2), 'P': Fr(p), 'Q': Fr(p + 1, p)}
    co = set()
    for n1, r1 in T.items():
        for y in F:
            if cls(y, p) == 1: continue
            for n2, r2 in T.items():
                S = [Fr(1), r1, y, y * r2]
                if all(ok(a, b, m) for a in S for b in S): co.add(''.join(sorted(n1 + n2)))
    print(p, 'p mod 6 =', p % 6, sorted(co))
