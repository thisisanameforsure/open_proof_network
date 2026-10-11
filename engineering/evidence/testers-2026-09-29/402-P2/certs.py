import json
from math import gcd, lcm
from functools import reduce
D='/home/user/open_proof_network/engineering/evidence/testers-2026-09-29/402-D/'
res={}
for f in ['sweep_small.json','sweep.json','sweep2.json','sweep3.json']:
    for k,v in json.load(open(D+f)).items():
        if v and int(k) not in res: res[int(k)]=v
def verify(n,cls):
    L=reduce(lcm,range(1,n),1)
    assert all(L%k==0 for k in range(1,n))
    S={L//k*j for k in range(1,n) for j in range(1,k)}
    idx={}
    for i,c in enumerate(cls):
        for v in c:
            if v in S and v not in idx: idx[v]=i
    for s in S:
        # findIdx: first class containing s
        i=next(i for i,c in enumerate(cls) if s in c)
        assert i < n-2, (n,s,i)
    for i in range(min(len(cls),n-2)):
        c=cls[i]
        for v in c:
            for w in c:
                if v!=w: assert n*gcd(v,w)<=v or n*gcd(v,w)<=w,(n,v,w)
    return L,len(S),sum(len(c)**2 for c in cls[:n-2])
if __name__=="__main__":
    for n in [9,10,15,16,21,22,25,26,27,28]:
        print(n, verify(n,res[n]))
