import sys, time
from fractions import Fraction
sys.path.insert(0, '.')
from greedy_exact import greedy
from greedy_fast import run
for p,q in [(1,2),(1,4),(3,8),(1,16)]:
    t=time.time()
    A1, status, n, log = greedy(Fraction(p,q), 2500)
    A2, cseq, dev, sel, flags, cnt = run(p,q,2500)
    # compare u values too: log has (n, float(u)) for exact
    ue = dict(log)
    maxd = max(abs(ue[m] - (dev[m]+0.5)) for m in ue if m < 2500)
    print(p,q,status, A1==A2[:len(A1)], len(A1), len(A2), "flags", flags, "max|u diff|", maxd, f"{time.time()-t:.1f}s")
