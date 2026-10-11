# Is each term 9^n W(n) A(n,k) (and the numerator pieces) an integer on its own?
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
def W(n, fact=True):
    w = F(factorial(max(n - 2, 0))) if fact else F(1)
    for k in range(1, n + 1): w *= (1 - c * two ** k)
    for k in range((n + 1) // 2, n + 1): w *= (1 - two ** k)
    return w
fails = []; fails_nofact = []
for n in range(1, 31):
    N = F(9) ** n * W(n); N2 = F(9) ** n * W(n, False)
    for k in range(1, n + 1):
        if (N * A(n, k)).denominator != 1: fails.append((n, k))
        if (N2 * A(n, k)).denominator != 1: fails_nofact.append((n, k))
print("per-term 9^n W(n) A(n,k) non-integral (n<=30):", fails[:20], "count", len(fails))
print("same without (n-2)!:", fails_nofact[:20], "count", len(fails_nofact))
