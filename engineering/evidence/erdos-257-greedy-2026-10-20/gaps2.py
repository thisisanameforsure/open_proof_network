from fractions import Fraction
from math import gcd
from collections import defaultdict
NMAX = 48
t = {n: Fraction(1, 2**n-1) for n in range(1, NMAX+120)}
Tlo = {n: sum(t[k] for k in range(n+1, n+100)) for n in range(0, NMAX+1)}
Thi = {n: Tlo[n] + Fraction(2, 2**(n+99)) for n in range(0, NMAX+1)}
E = float(Tlo[0])
print("E =", E)
tot = 0
for M in range(1, 11):
    g = float(t[M] - Tlo[M]); tot += 2**(M-1)*g
    print(f"M={M:2d}  g_M={g:.3e}  (2/3)4^-M={2/3*4**-M:.3e}  level measure 2^(M-1)g_M={2**(M-1)*g:.4e}  2^-M/3={2**-M/3:.4e}")
print(f"total failing measure (M<=10): {tot:.5f}  -> measure of the subset-sum set ~ {E-tot:.5f}")
def walk(x):
    r = x; F = []
    for n in range(1, NMAX+1):
        if r >= t[n]: r -= t[n]; F.append(n)
        if r == 0: return "finite", n, F
        if r > Thi[n]: return "fail", n, F
        if r > Tlo[n]: return "ambiguous", n, F
    return "open", NMAX, F
fails = defaultdict(list); opens = []; finite = []
Q = 128
for q in range(1, Q+1):
    for p in range(1, int(E*q)+1):
        if gcd(p, q) != 1: continue
        st, n, F = walk(Fraction(p, q))
        {"fail": lambda: fails[n].append((p, q, F)), "open": lambda: opens.append((p, q)),
         "finite": lambda: finite.append((p, q, F)), "ambiguous": lambda: print("AMBIG", p, q)}[st]()
total = sum(len(v) for v in fails.values()) + len(opens) + len(finite)
print(f"\nall p/q in (0,E) with q<={Q}: {total} fractions")
print("fail step M : count : heuristic sum_q q*2^-M/3")
for M in sorted(fails):
    print(f"  {M:2d} : {len(fails[M]):5d} : {sum(q for q in range(1,Q+1))*2.0**-M/3:8.1f}")
print(f"  open through {NMAX}: {len(opens)}   finite subset sums: {len(finite)}")
print("finite:", [(f"{p}/{q}", F) for p, q, F in finite])
print("open, by denominator:", sorted(opens, key=lambda s: (s[1], s[0]))[:60])
print("\nfail step per numerator, q = 2, 4, 8, 16, 32 (o = open):")
for q in [2, 4, 8, 16, 32]:
    row = []
    for p in range(1, int(E*q)+1):
        if gcd(p, q) != 1: continue
        st, n, F = walk(Fraction(p, q)); row.append(f"{p}:{'o' if st=='open' else n}")
    print(f"  q={q}: ", " ".join(row))
bad = 0
for M, lst in fails.items():
    for p, q, F in lst:
        x = Fraction(p, q); s = sum((t[a] for a in F if a < M), Fraction(0))
        if not (s + Tlo[M] < x < s + t[M]): bad += 1
print("\nfailures outside their predicted gap (sigma(F)+T_M, sigma(F)+t_M):", bad)
