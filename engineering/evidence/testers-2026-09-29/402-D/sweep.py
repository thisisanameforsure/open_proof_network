from math import gcd, lcm
from functools import reduce
import random, json, sys, time
def tabucol(S, conf, K, iters, seed):
    rnd=random.Random(seed); col={v:rnd.randrange(K) for v in S}; tabu={}
    cur=sum(1 for v in S for u in conf[v] if col[u]==col[v])//2
    for it in range(iters):
        if cur==0: return col
        bad=[v for v in S if any(col[u]==col[v] for u in conf[v])]
        best=None
        for v in bad:
            cnt=[0]*K
            for u in conf[v]: cnt[col[u]]+=1
            for c in range(K):
                if c==col[v]: continue
                delta=cnt[c]-cnt[col[v]]
                if tabu.get((v,c),-1)>it and cur+delta>0: continue
                if best is None or delta<best[0]: best=(delta,v,c)
        if best is None: continue
        d,v,c=best; tabu[(v,col[v])]=it+7+rnd.randrange(10); col[v]=c; cur+=d
    return None
res={}
for n in range(9,25):
    L=reduce(lcm,range(1,n)); S=sorted({L//k*j for k in range(2,n) for j in range(1,k)})
    conf={c:{d for d in S if d!=c and not (n*gcd(c,d)<=c or n*gcd(c,d)<=d)} for c in S}
    K=n-2; r=None
    for s in range(3):
        r=tabucol(S,conf,K,20000,s)
        if r: break
    classes=[sorted(v for v in S if r[v]==i) for i in range(K)] if r else None
    if r:
        for cl in classes: assert all(n*gcd(a,b)<=a or n*gcd(a,b)<=b for a in cl for b in cl if a!=b)
    res[n]=classes
    print(n, "L",L,"|S|",len(S),"K",K, "found" if r else "NOT found", time.strftime('%H:%M:%S')); sys.stdout.flush()
json.dump(res,open('sweep.json','w'))
