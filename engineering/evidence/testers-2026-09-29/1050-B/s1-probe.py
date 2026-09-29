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
res = []
for n in range(1, 21):
    p = {j: c * two ** j for j in range(1, n + 1)}
    D = {i: 1 for i in p}
    for i in p:
        for j in p:
            if j != i: D[i] *= (1 - p[j])
    X = sum(A(n, k) * sum(D[i] for i in range(1, k + 1)) for k in range(1, n + 1))
    QP = F(1)
    for k in range((n + 1) // 2, n + 1): QP *= (1 - two ** k)
    for e in range(0, 2 * n + 1):
        if (F(3) ** e * X).denominator == 1: break
    else: e = None
    res.append((n, e, (F(9) ** n * X).denominator, (F(9) ** n * X * QP).denominator))
print("(n, least e with 3^e X integral, denom of 9^n X, denom of 9^n X QP) where X = sum_k A_k sum_{i<=k} D_i:")
print(res)
