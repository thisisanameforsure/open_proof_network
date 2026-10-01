from math import gcd,lcm
from functools import reduce
import sys,time
sys.setrecursionlimit(10000)
def run(N,limit=20):
    L=reduce(lcm,range(1,N))
    V=sorted({L*j//k for k in range(2,N) for j in range(1,k)})
    bad={a:set(b for b in V if b!=a and N*gcd(a,b)>max(a,b)) for a in V}
    K=N-2
    col={}; cnt=[0]; t=time.time()
    def bt():
        cnt[0]+=1
        if time.time()-t>limit: raise TimeoutError
        unc=[v for v in V if v not in col]
        if not unc: return True
        v=max(unc,key=lambda u:(len({col[w] for w in bad[u] if w in col}),len(bad[u])))
        used={col[w] for w in bad[v] if w in col}
        mx=max(col.values(),default=-1)
        for c in range(min(K,mx+2)):
            if c not in used:
                col[v]=c
                if bt(): return True
                del col[v]
        return False
    try: r=bt()
    except TimeoutError: r=None
    return len(V),K,r,dict(col) if r else None
for N in range(3,21):
    n,K,r,c=run(N)
    print(N,"values",n,"colours",K,"colourable" if r else ("NOT" if r is False else "timeout"))
