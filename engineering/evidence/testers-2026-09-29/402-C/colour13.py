from math import gcd, lcm
import itertools, sys, json
N=13
L=1
for k in range(1,N): L=lcm(L,k)
S=sorted({L//k*j for k in range(2,N) for j in range(1,k)})
print("N",N,"L",L,"|S|",len(S))
def conflict(a,b): return N*gcd(a,b) > max(a,b)
adj={a:{b for b in S if b!=a and conflict(a,b)} for a in S}
K=N-2
col={}
def pick():
    best=None;bk=None
    for a in S:
        if a in col: continue
        key=(len({col[b] for b in adj[a] if b in col}),len(adj[a]))
        if bk is None or key>bk: bk=key;best=a
    return best
def rec():
    if len(col)==len(S): return True
    a=pick(); used={col[b] for b in adj[a] if b in col}
    for c in range(K):
        if c not in used:
            col[a]=c
            if rec(): return True
            del col[a]
    return False
ok=rec(); print("colouring with",K,"classes:",ok)
classes=[sorted(a for a in S if col[a]==i) for i in range(K)]
bad=[(a,b) for cl in classes for a,b in itertools.combinations(cl,2) if conflict(a,b)]
print("classes",classes); print("sizes",[len(c) for c in classes],"pairs",sum(len(c)*(len(c)-1)//2 for c in classes),"bad",bad)
# independent re-check: every (j,k) value lands in exactly one class
vals=[L//k*j for k in range(2,N) for j in range(1,k)]
assert all(sum(v in c for c in classes)==1 for v in vals)
json.dump(classes,open('classes13.json','w'))
