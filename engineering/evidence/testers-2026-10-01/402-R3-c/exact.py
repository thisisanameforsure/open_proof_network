# exact maximum |S| for given X (k general), compared with needed n-|X|
import sys, itertools
from math import gcd
from numk import lcmupto
sys.setrecursionlimit(100000)
def mis_max(V,n):
    V=sorted(V); nb={s:set() for s in V}
    for s in V:
        if s<n: continue
        for t in V:
            if t!=s and s>=n*gcd(s,t): nb[s].add(t); nb[t].add(s)
    best=[0,None]
    def rec(cand,chosen):
        if len(chosen)+len(cand)<=best[0]: return
        v=None; dv=0
        for c in cand:
            d=len(nb[c]&cand)
            if d>dv: v=c; dv=d
        if v is None:
            best[0]=len(chosen)+len(cand); best[1]=sorted(chosen|cand); return
        if dv==1:
            # degree-1 vertex world: take all leaves greedily: pick v's neighbour? simple: fallthrough
            pass
        rec(cand-{v}-nb[v],chosen|{v})
        rec(cand-{v},chosen)
    rec(set(V),set())
    return best
k=int(sys.argv[1]); lo=int(sys.argv[2]); hi=int(sys.argv[3]); Xs=[tuple(int(c) for c in a.split(',')) for a in sys.argv[4:]]
def isprime(q): return q>1 and all(q%d for d in range(2,int(q**.5)+1))
M=lcmupto(k)
for n in range(lo,hi):
    for p in range(2,n):
        if not (k*p < n <= (k+1)*p) or not isprime(p): continue
        def ok(x,s):
            P=x*s; d=gcd(P,M)
            return M//d <= k and P//d < n and (P//d)%p!=0
        out=[]
        for X in Xs:
            A=[s for s in range(1,n*M) if s%p and all(ok(x,s) for x in X)]
            b=mis_max(A,n)
            out.append((X,len(A),b[0],"need",n-len(X), b[1] if n<=22 else ''))
        print(n,p,out,flush=True)
