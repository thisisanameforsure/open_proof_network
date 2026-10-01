# Does beta0(n) (sum of partial-fraction coefficients) equal -p_n(8/3, 2), Borwein's q-Pade denominator
# p_n = sum_{k<n} (-c)^k 2^(k(k+3)/2) [n-1, k]_2 [n+k-1, n-1]_2  (lean-gallery Pade.lean `pVal`)?
from fractions import Fraction as F
c = F(8, 3); two = F(2)
def qbin(m, j):
    if j < 0 or j > m: return F(0)
    r = F(1)
    for i in range(j): r *= (two ** (m - i) - 1) / (two ** (i + 1) - 1)
    return r
def A(n, k):
    num = F(1)
    for t in range(1, n): num *= (1 - c * two ** (t + k))
    den = F(1)
    for l in range(1, n + 1):
        if l != k: den *= (1 - two ** (l - k))
    return -num / den
ok = True
for n in range(1, 21):
    b0 = sum(A(n, k) for k in range(1, n + 1))
    pv = sum((-c) ** k * two ** (k * (k + 3) // 2) * qbin(n - 1, k) * qbin(n + k - 1, n - 1) for k in range(n))
    if b0 != -pv: ok = False; print("differs at n =", n, b0, -pv)
print("beta0(n) == -pVal(n) for n = 1..20:", ok)
