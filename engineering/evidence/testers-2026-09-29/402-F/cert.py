import math, sys, random
from functools import reduce
def lcm(a,b): return a*b//math.gcd(a,b)
def cert(n, tries=2000, seed=0):
    L=reduce(lcm,range(1,n),1)
    S=sorted({L*j//k for k in range(2,n) for j in range(1,k)})
    good=lambda a,b: n*math.gcd(a,b)<=max(a,b)
    bad={a:{b for b in S if b!=a and not good(a,b)} for a in S}
    colours=n-2
    # DSatur with random restarts; then backtracking fallback
    rnd=random.Random(seed)
    best=None
    for t in range(tries):
        col={}
        order=list(S); rnd.shuffle(order)
        ok=True
        while len(col)<len(S):
            # pick uncoloured vertex with max saturation
            def sat(v): return (len({col[u] for u in bad[v] if u in col}), len(bad[v]), rnd.random())
            v=max((v for v in S if v not in col), key=sat)
            used={col[u] for u in bad[v] if u in col}
            free=[c for c in range(colours) if c not in used]
            if not free: ok=False; break
            col[v]=free[0]
        if ok: return L,S,col
    return L,S,None
if __name__=='__main__':
    for n in map(int,sys.argv[1:]):
        L,S,col=cert(n)
        print(n, 'L=',L,'|S|=',len(S),'colours',n-2,'found' if col else 'NOT FOUND')
