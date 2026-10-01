# K2: X,S nonempty sets of positive ints, forall x,s: Q(x,s) < n and p !| x*s, where Q = xs/2 if even else xs; |X|+|S| >= n
# claim (n>=9, 2p<n<=3p): X={1} or S={1}
import sys
def run(n,p):
    U=[x for x in range(1,2*n) if x%p]
    def ok(x,s):
        q=x*s
        if q%p==0: return False
        return (q//2 if q%2==0 else q) < n
    comp={x:frozenset(s for s in U if ok(x,s)) for x in U}
    res=[]
    # enumerate X via DFS, S = intersection
    def dfs(i, X, S):
        if X and len(X)+len(S) >= n and X!=[1]:
            # S may be any subset; need S != {1} possible with |X|+|S|>=n
            if not (len(S)==1 and 1 in S): res.append((list(X), sorted(S)))
        for j in range(i,len(U)):
            x=U[j]
            S2 = S & comp[x] if X else comp[x]
            # bound: remaining potential
            if len(S2)==0: continue
            if len(X)+1+ (len(U)-j-1) + len(S2) < n: continue
            dfs(j+1, X+[x], S2)
    dfs(0,[],frozenset())
    return res
for n in range(5,31):
    for p in range(2,n):
        if 2*p<n<=3*p:
            r=run(n,p)
            print(n,p,len(r), r[:3])
