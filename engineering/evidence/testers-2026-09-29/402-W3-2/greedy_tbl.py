# Largest-degree-first greedy (n-2)-colouring of the conflict graph on S_n = {L/k*j : 1<=j<k<n},
# c ~ d iff n*gcd(c,d) > max(c,d) (i.e. neither n*gcd<=c nor n*gcd<=d). Output tbl[k][j] = class.
import json,sys
from math import gcd,lcm
from functools import reduce
def colour(n,seed=None):
    L=reduce(lcm,range(1,n),1)
    S=sorted({L//k*j for k in range(1,n) for j in range(1,k)})
    conf=lambda c,d: not (n*gcd(c,d)<=c or n*gcd(c,d)<=d)
    adj={s:[t for t in S if t!=s and conf(s,t)] for s in S}
    order=sorted(S,key=lambda s:-len(adj[s]))
    col={}
    for s in order:
        used={col[t] for t in adj[s] if t in col}
        c=0
        while c in used: c+=1
        col[s]=c
    k=max(col.values())+1
    return L,S,col,k
def check(n,L,tbl):
    S={}
    for k in range(1,n):
        for j in range(1,k):
            i=tbl[k][j]; assert i<n-2
            S.setdefault(i,set()).add(L//k*j)
    for i,c in S.items():
        for v in c:
            for w in c:
                if v!=w: assert n*gcd(v,w)<=v or n*gcd(v,w)<=w
    return sum(len(c)**2 for c in S.values())
if __name__=='__main__':
    out={}
    for n in [int(x) for x in sys.argv[1].split(',')]:
        L,S,col,k=colour(n)
        ok=k<=n-2
        tbl=[[ (col[L//kk*j] if (kk>0 and j>0) else 0) for j in range(kk)] for kk in range(n)] if ok else None
        sq=check(n,L,tbl) if ok else None
        print(n,'|S|',len(S),'colours',k,'need',n-2,'ok',ok,'sumsq',sq,flush=True)
        if ok: out[n]=tbl
    json.dump(out,open(sys.argv[2],'w'))
