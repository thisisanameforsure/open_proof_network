from math import gcd, lcm
from itertools import combinations, product
from functools import reduce
def G(A): return max(a//gcd(a,b) for a in A for b in A)
def strip(a,p):
    e=0
    while a%p==0:a//=p;e+=1
    return a,e
print("E2 fibre form: k=#distinct p-free parts, m=max fibre size. Claim X: G>=k*m. Claim Y (all that the two branches give): G>=max(k,p^(m-1)).")
for p in (2,3):
  for n,R in [(3,16),(4,16),(5,16),(6,16)]:
    exX=None
    for S in combinations(range(1,R+1),n):
        if reduce(gcd,S)!=1: continue
        f={}
        for a in S:
            c,e=strip(a,p); f.setdefault(c,[]).append(e)
        k=len(f); m=max(map(len,f.values())); g=G(S)
        assert g>=max(k,p**(m-1))
        if g<k*m and exX is None: exX=(S,g,k,m)
    print(" p",p,"n",n,"first counterexample to X (set,G,k,m):",exX)
print("E3 lattice (Ahlswede-Daykin) form: #distinct gcd(a,L/b) >= n, L=lcm(A); vs #distinct a/gcd(a,b)")
for n,R in [(3,30),(4,26),(5,22),(6,20),(7,19)]:
    mn=99;first=None
    for S in combinations(range(1,R+1),n):
        L=reduce(lcm,S); c=len({gcd(a,L//b) for a in S for b in S}); mn=min(mn,c)
    print(" n",n,"min #gcd(a,L/b) =",mn)
S=(2,3,4,6,9,12,18);L=36
print(" S=",S,"quotients",sorted({a//gcd(a,b) for a in S for b in S}),"gcd(a,L/b)",sorted({gcd(a,L//b) for a in S for b in S}))
print("E4 CRT analogue for n=pq: T(p,q)=max size of a set of numbers p^e q^f with all quotients < pq")
for p,q in [(2,3),(2,5),(3,5),(2,7),(3,7),(5,7)]:
    n=p*q; pts=[(e,f) for e in range(8) for f in range(8) if p**e*q**f< n*n]
    # all elements can be normalised gcd 1; quotients<n => elements divide ... brute force by clique search
    vals=sorted(p**e*q**f for e in range(12) for f in range(12) if p**e*q**f<n**2)
    best=[]
    def ok(a,b): g=gcd(a,b); return a//g<n and b//g<n
    def ext(cur,cand):
        global best
        if len(cur)>len(best): best=cur[:]
        if len(cur)+len(cand)<=len(best): return
        for i,v in enumerate(cand):
            ext(cur+[v],[w for w in cand[i+1:] if ok(v,w)])
    ext([1],[v for v in vals[1:] if ok(1,v)])  # contains 1 wlog? (not wlog; reported as lower bound)
    phi=(p-1)*(q-1)
    print(f" p={p} q={q} n={n}: phi(n)={phi}, fibre containing 1 can have {len(best)} elements {best}; counting bound n <= {phi}*{len(best)}={phi*len(best)} (need < {n})")
A=[1,2,3,4,5,10,15,20]
print(" explicit n=6: A=",A,"classes mod 6 of the {2,3}-free part: 1 and 5, fibres {1,2,3,4} x {1,5}; within-fibre quotients:",G([1,2,3,4]),"G(A)=",G(A))
