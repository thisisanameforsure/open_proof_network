# For k*k<=n<=N: n where no prime p<=n//k has n%p < k%p (residue-only failures), and true exceptions (minFac C(n,k) > n//k).
import sys
from math import comb
K=int(sys.argv[1]); N=int(sys.argv[2])
m=N
s=bytearray([1])*(m+1); s[0]=s[1]=0
for i in range(2,int(m**.5)+1):
    if s[i]: s[i*i::i]=bytearray(len(s[i*i::i]))
P=[i for i in range(m+1) if s[i]]
fails=[];true=[]
for k in range(2,K+1):
    for n in range(k*k,N+1):
        b=n//k
        ok=False
        for p in P:
            if p>b: break
            if n%p < k%p: ok=True; break
        if not ok:
            fails.append((n,k))
print("residue-only failures:",fails[:200], "count",len(fails))
