"""Greedy (= unique) expansion of a rational x as a sum of 1/(2^a - 1), a in A.

Each term exceeds the sum of all later terms, so the subset-sum set S is a Cantor
set and x in S has exactly one representation.  The greedy walk either
  * terminates (r = 0): x is a finite subsum (odd denominator only),
  * gets stuck (r > tail_n after step n): x is not in S,
  * or continues forever: x in S with A infinite (a counterexample to #257).
Exact arithmetic with Fractions; tail_n computed as an exact upper bound.
"""
from fractions import Fraction
import sys

def term(a):
    return Fraction(1, 2**a - 1)

def tail_upper(n, extra=60):
    """Exact-rational upper bound for sum_{m>n} 1/(2^m-1): finitely many exact terms
    plus the geometric bound 2^{-(n+extra)} * 2 for the rest (each term < 2*2^{-m})."""
    s = sum(term(m) for m in range(n + 1, n + extra + 1))
    s += Fraction(2, 2 ** (n + extra))
    return s

def tail_lower(n, extra=60):
    return sum(term(m) for m in range(n + 1, n + extra + 1))

def greedy(x, nmax, verbose=False):
    r = Fraction(x)
    A = []
    log = []
    for n in range(1, nmax + 1):
        t = term(n)
        if r >= t:
            r -= t
            A.append(n)
        if r == 0:
            return A, "finite", n, log
        # stuck test: r must be <= tail_n (achievable by later terms)
        if r > tail_upper(n):
            return A, "stuck", n, log
        # margin: how close to the stuck window.  u = 2^n r in [0, 1+delta]
        u = r * 2 ** n
        log.append((n, float(u)))
    return A, "open", nmax, log

if __name__ == "__main__":
    p, q = int(sys.argv[1]), int(sys.argv[2])
    nmax = int(sys.argv[3]) if len(sys.argv) > 3 else 400
    A, status, n, log = greedy(Fraction(p, q), nmax)
    print(f"x={p}/{q}: {status} at n={n}; |A|={len(A)}")
    print("A =", A[:80], "..." if len(A) > 80 else "")
    gaps = [b - a for a, b in zip(A, A[1:])]
    print("gaps =", gaps[:80])
    # closeness to stuck: u_n near 1/2 from below within 2^-n/6 is the danger zone
    worst = sorted(((abs(u - 0.5), n) for n, u in log))[:5]
    print("u_n closest to 1/2:", worst)
