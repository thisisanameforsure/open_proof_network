# Lemma I: T subset of {odd t<n} U {even b<2n}, no multiple of p, cross pairs (odd t, even b): b < n*gcd(b,t).  claim |T| <= n-2
from math import gcd
import sys
sys.setrecursionlimit(10000)
def maxmatch(L, R, adj):
    mr = {}
    def aug(u, seen):
        for v in adj[u]:
            if v in seen: continue
            seen.add(v)
            if v not in mr or aug(mr[v], seen):
                mr[v] = u; return True
        return False
    return sum(aug(u, set()) for u in L)
bad=[]
for n in range(5, 260):
    for p in range(2, n):
        if not (2*p < n <= 3*p): continue
        O=[t for t in range(1,n,2) if t%p]
        E=[b for b in range(2,2*n,2) if b%p]
        adj={t:[b for b in E if b >= n*gcd(b,t)] for t in O}
        m=maxmatch(O,E,adj)
        mx=len(O)+len(E)-m
        if mx > n-2: bad.append((n,p,mx))
print("lemma I violations (n,p,max):", bad)
