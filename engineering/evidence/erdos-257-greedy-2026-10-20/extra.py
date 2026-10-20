import sys, numpy as np
from collections import Counter
d = np.load(sys.argv[1]); A = d["A"]; sel = d["sel"]; N = len(sel) - 1
ind = np.zeros(N + 2, dtype=bool); ind[A] = True
m = np.arange(1, N)
inA = ind[m]; nxt = ind[m + 1]
even = m % 2 == 0
print("P(m+1 in A | m in A, m even) =", round(nxt[inA & even].mean(), 4), " n=", (inA & even).sum())
print("P(m+1 in A | m in A, m odd ) =", round(nxt[inA & ~even].mean(), 4), " n=", (inA & ~even).sum())
print("P(m+1 in A | m not in A, m even) =", round(nxt[~inA & even].mean(), 4))
print("P(m+1 in A | m not in A, m odd ) =", round(nxt[~inA & ~even].mean(), 4))
for q in [3, 4]:
    for r in range(q):
        mask = inA & (m % q == r)
        print(f"  P(m+1 in A | m in A, m = {r} mod {q}) = {nxt[mask].mean():.4f}")
gaps = np.diff(A)
print("\nconsecutive-gap transition P(next gap = g' | gap = g), rows g=1..6, cols g'=1..6 (coin: 1/2,1/4,1/8,...):")
for g in range(1, 7):
    nx = gaps[1:][gaps[:-1] == g]
    c = Counter(nx.tolist()); n = len(nx)
    print(f"  g={g} n={n:6d}: " + " ".join(f"{c[h]/n:.4f}" for h in range(1, 7)))
# first 200 elements written as a 0/1 strip in rows of 50, to eyeball
x = ind[1:201].astype(int)
print("\nindicator of A, positions 1..200 in rows of 50:")
for i in range(0, 200, 50):
    print(f"{i+1:4d}: " + "".join("#" if v else "." for v in x[i:i+50]))
