# General-k block numerics for erdos-402.  kp < n <= (k+1)p, M = lcm(1..k).
# Block analysis (402-R2-c few_or_most): multiples of p are a = pMG/x (x in X), non-multiples b = G*s (s in S),
# pair condition: with P = x*s, d = gcd(P, M):  M/d <= k,  P/d < n,  p !| P/d.
# S-S condition: s < n*gcd(s,t).  X-X condition: x' < n*gcd(x,x') (a/gcd(a,a') = x'/gcd(x,x')).
# Question: which X (|X| = u >= 1) admit S with |S| = n - u ?   ("few" side: any u; we enumerate all X)
import sys, itertools, os
STRICTX=not os.environ.get("NOSTRICTX"); NOPY=bool(os.environ.get("NOPY"))
from math import gcd
sys.setrecursionlimit(100000)
def lcmupto(k):
    r=1
    for i in range(1,k+1): r=r*i//gcd(r,i)
    return r
def maxmatch(L, adj):
    mr = {}
    def aug(u, seen):
        for v in adj[u]:
            if v in seen: continue
            seen.add(v)
            if v not in mr or aug(mr[v], seen):
                mr[v] = u; return True
        return False
    return sum(aug(u, set()) for u in L)
def mis_exact(V, n, need):
    # is there an independent set of size >= need in conflict graph on V (conflict: s >= n*gcd(s,t) or t >= n*gcd(s,t))
    V=sorted(V)
    nb={s:set() for s in V}
    for s in V:
        if s<n: continue
        for t in V:
            if t!=s and s >= n*gcd(s,t): nb[s].add(t); nb[t].add(s)
    best=[None]
    def rec(cand, chosen):
        if best[0] is not None: return
        if len(chosen)+len(cand) < need: return
        # pick vertex with max degree in cand
        v=None; dv=0
        for c in cand:
            d=len(nb[c]&cand)
            if d>dv: v=c; dv=d
        if v is None:
            best[0]=sorted(chosen|cand); return
        rec(cand-{v}, chosen)            # exclude v (high degree) first
        rec(cand-{v}-nb[v], chosen|{v})
    rec(set(V), set())
    return best[0]
def run(n,p,k,verbose=True):
    M=lcmupto(k)
    def ok(x,s):
        P=x*s; d=gcd(P,M)
        return M//d <= k and P//d < n and (NOPY or (P//d)%p!=0)
    U=[s for s in range(1,n*M) if s%p]
    def allowed(X): return [s for s in U if all(ok(x,s) for x in X)]
    cand=[]
    for x in range(1,n*M):
        A=[s for s in U if ok(x,s)]
        if len(A) >= n-1 - 0 or len(A) >= n-2*M: cand.append(x)
    surv=[]
    # enumerate subsets X of cand, pairwise strict, DFS
    def bound(X,A):
        need=n-len(X)
        if len(A)<need: return None
        small=[s for s in A if s<n]; big=[s for s in A if s>=n]
        adj={b:[t for t in small if b>=n*gcd(b,t)] for b in big}
        m=maxmatch(big,adj)
        if len(A)-m < need: return None
        return mis_exact(A,n,need)
    def dfs(i,X,A):
        for j in range(i,len(cand)):
            x=cand[j]
            if STRICTX and any(x>=n*gcd(x,y) or y>=n*gcd(x,y) for y in X): continue
            A2=[s for s in A if ok(x,s)]
            X2=X+[x]
            if len(A2) <= n-2*M: continue   # u < 2M so |S| = n-u > n-2M
            r=bound(X2,A2)
            if r is not None: surv.append((X2,r))
            dfs(j+1,X2,A2)
    dfs(0,[],U)
    return cand,surv
if __name__=="__main__":
    k=int(sys.argv[1]); lo=int(sys.argv[2]); hi=int(sys.argv[3]); allp = len(sys.argv)>4
    def isprime(q): return q>1 and all(q%d for d in range(2,int(q**.5)+1))
    for n in range(lo,hi):
        for p in range(2,n):
            if not (k*p < n <= (k+1)*p): continue
            if not allp and not isprime(p): continue
            cand,surv=run(n,p,k)
            print(n,p,"cand",cand[:12],"survivors",len(surv),[(X, S if len(S)<40 else len(S)) for X,S in surv[:4]],flush=True)
