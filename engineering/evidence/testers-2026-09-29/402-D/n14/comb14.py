from math import gcd, lcm
from functools import reduce
import random, json
NN=14; N=NN; K0=NN-2
L = reduce(lcm, range(1,N))
S = sorted({L//k*j for k in range(2,N) for j in range(1,k)})
def ok(c,d): return NN*gcd(c,d) <= c or NN*gcd(c,d) <= d
conf = {c:{d for d in S if d!=c and not ok(c,d)} for c in S}
print("L",L,"|S|",len(S),"max deg",max(len(v) for v in conf.values()))
# tabu search colouring with K colours
def tabucol(K, iters=200000, seed=0):
    rnd=random.Random(seed)
    col={v:rnd.randrange(K) for v in S}
    tabu={}
    def conflicts(): return sum(1 for v in S for u in conf[v] if col[u]==col[v])//2
    cur=conflicts()
    for it in range(iters):
        if cur==0: return col
        bad=[v for v in S if any(col[u]==col[v] for u in conf[v])]
        best=None
        for v in bad:
            for c in range(K):
                if c==col[v]: continue
                delta=sum(1 for u in conf[v] if col[u]==c)-sum(1 for u in conf[v] if col[u]==col[v])
                if tabu.get((v,c),-1)>it and cur+delta>0: continue
                if best is None or delta<best[0]: best=(delta,v,c)
        if best is None: continue
        d,v,c=best; tabu[(v,col[v])]=it+7+rnd.randrange(10); col[v]=c; cur+=d
    return None
for K in (K0,K0-1):
    r=None
    for s in range(5):
        r=tabucol(K,20000,s)
        if r: break
    print(K, "found" if r else "not found")
    if K==K0 and r:
        classes=[sorted(v for v in S if r[v]==i) for i in range(K0)]
        for cl in classes: assert all(ok(a,b) for a in cl for b in cl if a!=b)
        assert sorted(sum(classes,[]))==S
        json.dump(classes,open('classes.json','w')); print(classes, sum(len(c)**2 for c in classes))
