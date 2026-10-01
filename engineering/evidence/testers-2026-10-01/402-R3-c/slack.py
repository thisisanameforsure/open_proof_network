# for each X subset of small candidates: bipartite (small<n vs big>=n) upper bound on |S| minus needed n-|X|
import sys, itertools
from math import gcd
from numk import lcmupto, maxmatch
k=int(sys.argv[1]); lo=int(sys.argv[2]); hi=int(sys.argv[3]); step=int(sys.argv[4]) if len(sys.argv)>4 else 1
def isprime(q): return q>1 and all(q%d for d in range(2,int(q**.5)+1))
M=lcmupto(k)
worst={}
for n in range(lo,hi,step):
    for p in range(2,n):
        if not (k*p < n <= (k+1)*p) or not isprime(p): continue
        def ok(x,s):
            P=x*s; d=gcd(P,M)
            return M//d <= k and P//d < n and (P//d)%p!=0
        U=[s for s in range(1,n*M) if s%p]
        A1={x:[s for s in U if ok(x,s)] for x in range(1,n*M//max(1,(n-2*M)) +2*M)}
        cand=[x for x in A1 if len(A1[x])>=n-2*M]
        row=[]
        for r in range(1,len(cand)+1):
            for X in itertools.combinations(cand,r):
                if any(a!=b and a>=n*gcd(a,b) for a in X for b in X): continue
                A=[s for s in U if all(ok(x,s) for x in X)]
                small=[s for s in A if s<n]; big=[s for s in A if s>=n]
                adj={b:[t for t in small if b>=n*gcd(b,t)] for b in big}
                m=maxmatch(big,adj)
                sl=(len(A)-m)-(n-len(X))
                row.append((X,len(A)-n+len(X),sl))
                if sl>worst.get(X,(-99,))[0]: worst[X]=(sl,n,p)
        print(n,p,[(X,c,s) for X,c,s in row if s>=-3 or len(X)==1],flush=True)
print("worst slack per X (>= 0 means bipartite bound fails):")
for X in sorted(worst,key=lambda X:-worst[X][0])[:25]: print(X,worst[X])
