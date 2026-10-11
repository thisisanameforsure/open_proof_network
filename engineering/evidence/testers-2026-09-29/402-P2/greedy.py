import sys, json
from math import gcd, lcm
from functools import reduce
lo,hi=int(sys.argv[1]),int(sys.argv[2])
fails=[]
for n in range(lo,hi+1):
    L=reduce(lcm,range(1,n),1)
    S=sorted({L//k*j for k in range(1,n) for j in range(1,k)})
    N=len(S); K=n-2
    adj=[[j for j in range(N) if j!=i and n*gcd(S[i],S[j])>max(S[i],S[j])] for i in range(N)]
    col=[-1]*N
    for i in sorted(range(N),key=lambda i:-len(adj[i])):
        used={col[j] for j in adj[i] if col[j]>=0}
        c=next((c for c in range(K) if c not in used),None)
        if c is None: fails.append(n); break
        col[i]=c
    else:
        print(n,N,"greedy ok, colours used",max(col)+1,"of",K,flush=True); continue
    print(n,N,"greedy FAILED",flush=True)
print("fails",fails)
