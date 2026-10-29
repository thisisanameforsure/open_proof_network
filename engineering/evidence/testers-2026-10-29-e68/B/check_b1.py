# sanity check of B-1 (truncation) and B-2 (recurrence) with exact rationals; not a result for the record
from fractions import Fraction as Fr
from math import factorial as f, log, ceil, floor
def frac(q): return q - (q.numerator // q.denominator)
for N in [10,20,30,40,60]:
    F = sum(Fr(f(N), f(n)-1) for n in range(2,N+1))
    G = sum(Fr(f(N)//f(n), f(n)-1) for n in range(2,N+1))
    assert frac(F)==frac(G)
    # smallest cut with tail < 1/N
    cut=None
    for c in range(2,N+1):
        L = sum(Fr(f(N)//f(n), f(n)-1) for n in range(c+1,N+1))
        if L < Fr(1,N): cut=c; break
    print(N, "x_N~%.6f"%float(frac(F)), "1-2/N=%.4f"%(1-2/N), "min cut", cut, "N/2+N/logN=%.1f"%(N/2+N/log(N)))
# recurrence
for N in range(2,30):
    F1 = sum(Fr(f(N), f(n)-1) for n in range(2,N+1)); F2=sum(Fr(f(N+1), f(n)-1) for n in range(2,N+2))
    assert F2 == (N+1)*F1 + 1 + Fr(1, f(N+1)-1)
print("recurrence ok")
