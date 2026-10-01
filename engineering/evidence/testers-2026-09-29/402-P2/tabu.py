import sys, random, json, time
from math import gcd, lcm
from functools import reduce
n=int(sys.argv[1]); seed=int(sys.argv[2]); iters=int(sys.argv[3])
random.seed(seed)
L=reduce(lcm,range(1,n),1)
S=sorted({L//k*j for k in range(1,n) for j in range(1,k)})
N=len(S); K=n-2
adj=[[j for j in range(N) if j!=i and n*gcd(S[i],S[j])>max(S[i],S[j])] for i in range(N)]
# DSatur init
col=[-1]*N
order=sorted(range(N),key=lambda i:-len(adj[i]))
for i in order:
    used={col[j] for j in adj[i] if col[j]>=0}
    free=[c for c in range(K) if c not in used]
    col[i]=free[0] if free else random.randrange(K)
# conflict counts
C=[[0]*K for _ in range(N)]
for i in range(N):
    for j in adj[i]: C[i][col[j]]+=1
f=sum(C[i][col[i]] for i in range(N))//2
tabu={}
best=f; t0=time.time()
for it in range(iters):
    if f==0: break
    bc=None;bd=10**9
    confl=[i for i in range(N) if C[i][col[i]]>0]
    for i in confl:
        ci=col[i]
        for c in range(K):
            if c==ci: continue
            d=C[i][c]-C[i][ci]
            if (tabu.get((i,c),-1)<it or f+d<best) and (d<bd or (d==bd and random.random()<0.3)):
                bd=d;bc=(i,c)
    if bc is None: continue
    i,c=bc; old=col[i]
    for j in adj[i]:
        C[j][old]-=1; C[j][c]+=1
    col[i]=c; f+=bd
    tabu[(i,old)]=it+int(0.6*len(confl))+random.randrange(10)
    if f<best: best=f
    if it%2000==0: print(it,f,best,round(time.time()-t0),flush=True)
print("final",f)
if f==0:
    cls=[[S[i] for i in range(N) if col[i]==c] for c in range(K)]
    json.dump({str(n):cls},open("found_%d.json"%n,"w"))
    print("FOUND")
