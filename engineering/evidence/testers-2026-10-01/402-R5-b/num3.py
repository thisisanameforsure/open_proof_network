# 402-R5-b num3: test the generalised rectangle lemma. For every n<=N, every prime p in (n,2n) with 2k<=n+2:
# for every shape (al,be) with gap(n,al) and gap(n,be) the brute-force failure set F(al,be) must be empty.
# Also count shapes where a gap fails but F is empty (criterion is sufficient, not necessary) and vice versa.
import sys
from num1 import fails, isp
from num2 import bad
N=int(sys.argv[1])
tested=viol=0; conv=0
for n in range(3,N+1):
    for p in range(n+1,2*n):
        if not isp(p): continue
        k=2*n-p
        if 2*k>n+2: continue
        B={b[0] for b in bad(n,k)}
        for al in range(n-k+1,n):
            be=p-al
            if al>be: continue
            F=fails(n,al,be)
            if al not in B and be not in B:
                tested+=1
                if F: viol+=1; print("VIOLATION",n,p,al,be,F)
            elif not F: conv+=1
print("N=%d shapes with both gaps tested=%d violations=%d ; shapes with a gap failure but no rectangle failure=%d"%(N,tested,viol,conv))
