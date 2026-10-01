# beta0(n) as a power-series coefficient: beta0 = [x^(n-1)] Q(x) / prod_k (1 - p_k x),
# Q(x) = -prod_{t=1..n-1} (x - 2^t), p_k = (8/3) 2^k. Check, and check 3^(n-1) beta0 is an integer.
from fractions import Fraction as F
c = F(8, 3); two = F(2)
def A(n, k):
    num = F(1)
    for t in range(1, n): num *= (1 - c * two ** (t + k))
    den = F(1)
    for l in range(1, n + 1):
        if l != k: den *= (1 - two ** (l - k))
    return -num / den
def polymul(a, b, N):
    r = [F(0)] * N
    for i, x in enumerate(a):
        for j, y in enumerate(b):
            if i + j < N: r[i + j] += x * y
    return r
ok1 = ok2 = True
for n in range(1, 21):
    N = n
    Q = [F(-1)]
    for t in range(1, n): Q = polymul(Q, [-two ** t, F(1)], N)
    S = [F(1)] + [F(0)] * (N - 1)
    for k in range(1, n + 1):
        g = [(c * two ** k) ** j for j in range(N)]
        S = polymul(S, g, N)
    coef = polymul(Q, S, N)[n - 1]
    b0 = sum(A(n, k) for k in range(1, n + 1))
    ok1 &= (coef == b0)
    ok2 &= ((F(3) ** (n - 1) * b0).denominator == 1)
print("beta0 == [x^(n-1)] Q/prod(1-p_k x) for n=1..20:", ok1)
print("3^(n-1) * beta0(n) integral for n=1..20:", ok2)
