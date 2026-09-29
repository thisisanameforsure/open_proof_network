# Audit of erdos-1050--h1-v2--h2 (hole `integrality`).
# Statement: exists a b : N -> Z, forall n >= 1,
#   b n * z - a n = R(n),  z = sum_{j>=0} (1 - c 2^(j+1))^-1,  c = 8/3,
#   R(n) = 9^n * W(n) * E(n),
#   W(n) = (n-2)! * prod_{k=1..n} (1 - c 2^k) * prod_{k=(n+1)//2..n} (1 - 2^k)   [n-2 is natural subtraction]
#   E(n) = sum_{j>=0} -(1 - c 2^(2n+j))^-1 * prod_{k=1..n-1} (1 - 2^(k-(n+j))) * (1 - c 2^(k+n+j))^-1
# Method: E(n) = sum_{m>=1} f(2^m) (terms m<n vanish), partial fractions in x = 2^m give
#   E(n) = beta0 * z - alpha0 with beta0, alpha0 rational (exact, Fractions);
#   then R(n) = beta*z - alpha with beta = 9^n W beta0, alpha = 9^n W alpha0.
# Since z is irrational (Borwein 1991), integers a_n, b_n exist iff beta, alpha are integers.
# Cross-check: E(n) summed directly with mpmath at 300 digits against beta0*z - alpha0.
from fractions import Fraction as F
from math import factorial
import sys, mpmath
mpmath.mp.dps = 300
q = 2; c = F(8, 3)

def exact(n):
    xk = lambda k: 1 / (c * F(q) ** k)
    A = {}
    for k in range(1, n + 1):
        num = F(1)
        for i in range(1, n):
            num *= (1 - c * F(q) ** (i + k))
        den = F(1)
        for l in range(1, n + 1):
            if l != k:
                den *= (1 - F(q) ** (l - k))
        A[k] = -num / den
    B = {i: sum(A[k] * (c * F(q) ** k) ** (-i) for k in A) for i in range(1, n)}
    s = lambda k: sum(1 / (1 - c * F(q) ** i) for i in range(1, k + 1))
    beta0 = sum(A.values())
    alpha0 = sum(A[k] * s(k) for k in A) - sum(B[i] / (F(q) ** i - 1) for i in B)
    W = F(factorial(max(n - 2, 0)))
    for k in range(1, n + 1):
        W *= (1 - c * F(q) ** k)
    for k in range((n + 1) // 2, n + 1):
        W *= (1 - F(q) ** k)
    N = F(9) ** n * W
    return beta0, alpha0, N

def mpf(fr): return mpmath.mpf(fr.numerator) / fr.denominator
cm = mpmath.mpf(8) / 3
z = mpmath.nsum(lambda j: 1 / (1 - cm * mpmath.mpf(2) ** (j + 1)), [0, mpmath.inf])
def E_direct(n):
    tot = mpmath.mpf(0)
    for j in range(0, 1200):
        t = -1 / (1 - cm * mpmath.mpf(2) ** (2 * n + j))
        for k in range(1, n):
            t *= (1 - mpmath.mpf(2) ** (k - (n + j))) / (1 - cm * mpmath.mpf(2) ** (k + n + j))
        tot += t
    return tot

print("z =", mpmath.nstr(z, 40))
print("3/5 - 3T check: T =", mpmath.nstr(mpmath.nsum(lambda n: 1/(mpmath.mpf(2)**(n+3)-3), [0, mpmath.inf]), 30))
for n in range(1, 13):
    beta0, alpha0, N = exact(n)
    Ed = E_direct(n)
    Ep = mpf(beta0) * z - mpf(alpha0)
    beta, alpha = N * beta0, N * alpha0
    R = mpf(N) * Ed
    print(f"n={n}: |E_direct - (beta0 z - alpha0)| = {mpmath.nstr(abs(Ed-Ep), 3)}; R(n) = {mpmath.nstr(R, 12)}")
    print(f"   beta  = {beta}  integer={beta.denominator == 1}")
    print(f"   alpha = {alpha}  integer={alpha.denominator == 1}")
    if beta.denominator != 1 or alpha.denominator != 1:
        print(f"   denominators: beta {beta.denominator}, alpha {alpha.denominator}")
