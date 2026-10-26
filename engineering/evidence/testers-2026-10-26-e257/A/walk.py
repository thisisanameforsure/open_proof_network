"""Exact greedy walk of 1/2 over e_n = 1/(2^n - 1), n >= 1 (e_0 = 0 as in Lean).

r_0 = 1/2; r_{m+1} = r_m - e_m if e_m <= r_m else r_m.  Step m is "taken" iff e_m <= r_m.
Checks the two open holes under spec-a70fcca4--h4--h1 and prints the structure of the skips.

usage: python3 walk.py DEPTH
"""
import sys
from fractions import Fraction as F

N = int(sys.argv[1]) if len(sys.argv) > 1 else 400

def e(n):
    return F(0) if n == 0 else F(1, 2**n - 1)

r = F(1, 2)
taken = []          # steps taken
skipped = []        # steps skipped (m >= 1)
rem = {}            # r_m at skipped m
for m in range(N + 1):
    em = e(m)
    if em <= r:
        taken.append(m)
        r = r - em
    else:
        skipped.append(m)
        rem[m] = r

skipped1 = [m for m in skipped if m >= 1]
print("greedy set below", N, ":", taken[:40], "...")
print("skipped steps:", skipped1[:60], "...")

# hole --h4--h1--h1 (W(2m), m >= 2) and --h4--h1--h2 (W(3m+2), m >= 1)
def next_skip(m):
    for n in skipped1:
        if n > m:
            return n
    return None

worst2 = (0, None)
worst3 = (0, None)
ok1 = ok2 = True
for m in skipped1:
    n = next_skip(m)
    if n is None:
        break
    if m >= 2 and not (n <= 2 * m):
        ok1 = False; print("W(2m) FAILS at", m, "next skip", n)
    if m >= 1 and not (n <= 3 * m + 2):
        ok2 = False; print("W(3m+2) FAILS at", m, "next skip", n)
    ratio = F(n - m, m)
    if ratio > worst2[0]:
        worst2 = (ratio, (m, n))
print("W(2m) m>=2 holds to depth", N, ":", ok1, "| W(3m+2) m>=1 holds:", ok2)
print("tightest (n-m)/m over skipped m:", worst2)

# bound of --h4--h1: at skipped m, r_m <= 2^-m + 4^-m/3 ; print margin in units of 4^-m
print("margins (B_m - r_m) * 4^m at the first skipped steps:")
for m in skipped1[:12]:
    B = F(1, 2**m) + F(1, 3 * 4**m)
    print("  m =", m, " r_m =", rem[m], " margin*4^m =", float((B - rem[m]) * 4**m))

# runs of consecutive taken steps
runs = []
cur = 0
for m in range(1, N + 1):
    if m in rem:
        if cur:
            runs.append((m - cur, m))
        cur = 0
    else:
        cur += 1
runs.sort(reverse=True)
print("longest runs (length, start):", runs[:8])
