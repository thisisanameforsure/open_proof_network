from math import gcd
import itertools, sys, random
L=360360
S=sorted({L//k*j for k in range(2,16) for j in range(1,k)})
print(len(S))
def conflict(a,b): return 16*gcd(a,b) > max(a,b)
adj={a:{b for b in S if b!=a and conflict(a,b)} for a in S}
print("max degree", max(len(v) for v in adj.values()))
# DSatur + backtracking for 14 colours
def colour(K):
    order=sorted(S,key=lambda a:-len(adj[a]))
    col={}
    sys.setrecursionlimit(10000)
    def pick():
        best=None;bk=None
        for a in S:
            if a in col: continue
            sat=len({col[b] for b in adj[a] if b in col})
            key=(sat,len(adj[a]))
            if bk is None or key>bk: bk=key;best=a
        return best
    def rec():
        if len(col)==len(S): return True
        a=pick()
        used={col[b] for b in adj[a] if b in col}
        for c in range(K):
            if c not in used:
                col[a]=c
                if rec(): return True
                del col[a]
        return False
    return col if rec() else None
for K in (14,):
    c=colour(K); print(K, c is not None)
    if c and K==14: best=c
c=best
classes=[sorted(a for a in S if c[a]==i) for i in range(14)]
for cl in classes: 
    assert all(not conflict(a,b) for a,b in itertools.combinations(cl,2))
print(classes)
print([len(x) for x in classes], sum(len(x)*(len(x)-1)//2 for x in classes))
import json; json.dump(classes,open('classes.json','w'))
