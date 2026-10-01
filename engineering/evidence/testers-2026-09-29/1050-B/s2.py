from fractions import Fraction as F
from math import factorial
c = F(8, 3); two = F(2)
def A(n, k):
    num = F(1)
    for t in range(1, n): num *= (1 - c * two ** (t + k))
    den = F(1)
    for l in range(1, n + 1):
        if l != k: den *= (1 - two ** (l - k))
    return -num / den
def W(n):
    w = F(factorial(max(n - 2, 0)))
    for k in range(1, n + 1): w *= (1 - c * two ** k)
    for k in range((n + 1) // 2, n + 1): w *= (1 - two ** k)
    return w
bad_term = []; minexp = {}
for n in range(1, 21):
    for i in range(1, n):
        B = sum(A(n, k) * (c * two ** k) ** (-i) for k in range(1, n + 1))
        if (F(9) ** n * W(n) * B / (two ** i - 1)).denominator != 1: bad_term.append((n, i))
        # smallest e with 3^e * 2^? * B integral (allow powers of 2 too)
        d = B.denominator
        while d % 2 == 0: d //= 2
        e = 0
        while d % 3 == 0: d //= 3; e += 1
        minexp[(n, i)] = (e, d)
print("(n,i) with 9^n W(n) B(n,i)/(2^i - 1) not an integer, n<=20:", bad_term)
print("B(n,i) denominators after removing 2s and 3s (should be 1):", sorted(set(v[1] for v in minexp.values())))
print("max 3-exponent in denominator of B(n,i) vs n-1:", [(n, max(minexp[(n, i)][0] for i in range(1, n))) for n in range(2, 21)])
mx2 = 0; sample = []
for n in range(1, 21):
    for i in range(1, n):
        B = sum(A(n, k) * (c * two ** k) ** (-i) for k in range(1, n + 1))
        d = B.denominator; v = 0
        while d % 2 == 0: d //= 2; v += 1
        mx2 = max(mx2, v)
        if (F(3) ** (n - 1) * B).denominator != 1: sample.append((n, i))
print("largest power of 2 in any B(n,i) denominator, n<=20:", mx2)
print("(n,i) with 3^(n-1) B(n,i) not an integer:", sample[:10], len(sample))
