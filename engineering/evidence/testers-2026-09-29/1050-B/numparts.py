# Which parts of alpha0 are integral after 9^n W(n)?  alpha0 = S1 - S2,
# S1 = sum_k A_k s_k (s_k = sum_{i<=k} 1/(1 - c 2^i)), S2 = sum_{i=1..n-1} B_i/(2^i - 1).
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
r1 = r2 = True; bad = []
for n in range(1, 26):
    N = F(9) ** n * W(n)
    S1 = sum(A(n, k) * sum(1 / (1 - c * two ** i) for i in range(1, k + 1)) for k in range(1, n + 1))
    S2 = sum(sum(A(n, k) * (c * two ** k) ** (-i) for k in range(1, n + 1)) / (two ** i - 1) for i in range(1, n))
    a, b = (N * S1).denominator == 1, (N * S2).denominator == 1
    if not (a and b): bad.append((n, a, b))
print("n where 9^n W S1 or 9^n W S2 is not an integer (n, S1 ok, S2 ok):", bad)
