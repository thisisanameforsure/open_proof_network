# Exact check of the `partial_fractions` hole as written in skeleton2.lean, n = 1..10, m = 1..12
from fractions import Fraction as F
c = F(8, 3); two = F(2)
def A(n, k):
    num = F(1)
    for t in range(1, n): num *= (1 - c * two ** (t + k))
    den = F(1)
    for l in range(1, n + 1):
        if l != k: den *= (1 - two ** (l - k))
    return -num / den
bad = 0
for n in range(1, 11):
    for m in range(1, 13):
        G = -1 / (1 - c * two ** (m + n))
        for k in range(1, n): G *= (1 - two ** (k - m)) * (1 / (1 - c * two ** (k + m)))
        R = sum(A(n, k) / (1 - c * two ** (k + m)) for k in range(1, n + 1))
        R += sum(sum(A(n, k) / (c * two ** k) ** i for k in range(1, n + 1)) / (two ** m) ** i for i in range(1, n))
        if G != R: bad += 1; print("MISMATCH", n, m)
print("partial_fractions exact check n=1..10, m=1..12: mismatches =", bad)
