from fractions import Fraction as F
c = F(8, 3); two = F(2)
def A(n, k):
    num = F(1)
    for t in range(1, n): num *= (1 - c * two ** (t + k))
    den = F(1)
    for l in range(1, n + 1):
        if l != k: den *= (1 - two ** (l - k))
    return -num / den
bad = []
for n in range(1, 16):
    for i in range(1, n + 1):
        T = sum(A(n, k) for k in range(i, n + 1))
        v = F(3) ** (n - 1) * T
        if v.denominator != 1: bad.append((n, i, v.denominator))
print("(n, i, denominator) where 3^(n-1) * sum_{k>=i} A(n,k) is not an integer:", bad[:15], "count", len(bad))
