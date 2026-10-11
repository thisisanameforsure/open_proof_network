from math import gcd, lcm
from functools import reduce
import sys
sys.setrecursionlimit(10000)
def run(N, limit=2_000_000):
    L=reduce(lcm,range(1,N))
    vals=sorted({L*j//k for k in range(2,N) for j in range(1,k)})
    bad={u:set(v for v in vals if v!=u and N*gcd(u,v)>max(u,v)) for u in vals}
    # DSatur backtracking for K = N-2 colours
    K=N-2
    col={}
    steps=[0]
    def pick():
        best=None;bk=None
        for u in vals:
            if u in col: continue
            sat=len({col[v] for v in bad[u] if v in col})
            key=(sat,len(bad[u]))
            if bk is None or key>bk: best,bk=u,key
        return best
    def bt():
        steps[0]+=1
        if steps[0]>limit: raise TimeoutError
        u=pick()
        if u is None: return True
        used={col[v] for v in bad[u] if v in col}
        for c in range(K):
            if c not in used:
                col[u]=c
                if bt(): return True
                del col[u]
            if c>=len(set(col.values())): break  # symmetry
        return False
    try: ok=bt()
    except TimeoutError: ok=None
    return L,len(vals),K,ok,dict(col) if ok else None
for N in [9,10,11,12,13,14,15,16,17,18]:
    L,n,K,ok,col=run(N)
    print(N,'L=',L,'values',n,'colours',K,'ok',ok)
    if ok:
        cls=[sorted(u for u in col if col[u]==c) for c in range(K)]
        print('  ',cls)
