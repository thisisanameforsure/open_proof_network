import math, sys
from functools import reduce
def maxclique(V, adj):
    best=[]
    def bk(R,P,X):
        nonlocal best
        if not P and not X:
            if len(R)>len(best): best=R[:]
            return
        if len(R)+len(P)<=len(best): return
        u=max(P|X,key=lambda v:len(adj[v]&P))
        for v in list(P-adj[u]):
            bk(R+[v],P&adj[v],X&adj[v]); P=P-{v}; X=X|{v}
    bk([],set(V),set()); return best
for n in range(3,17):
    L=reduce(lambda x,y:x*y//math.gcd(x,y),range(1,n))
    D=[d for d in range(1,L+1) if L%d==0]
    ok=lambda a,b: a//math.gcd(a,b)<=n-1 and b//math.gcd(a,b)<=n-1
    adj={a:{b for b in D if b!=a and ok(a,b)} for a in D}
    c=maxclique(D,adj)
    print(f"n={n}: divisors of lcm(1..{n-1})={len(D)}, largest set with all a/gcd(a,b)<=n-1: {len(c)} {sorted(c)}", flush=True)
