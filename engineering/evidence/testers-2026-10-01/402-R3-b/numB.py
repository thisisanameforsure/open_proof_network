# 402-R3-b: numerical tests of the "reduce composite n to its prime factors" readings.
from math import gcd, isqrt
from itertools import combinations
import random
def G(A):
    return max(a//gcd(a,b) for a in A for b in A)
def mk(A,k):  # min over k-subsets of G
    return min(G(S) for S in combinations(A,k))
print("== T0: min G over n-subsets of [1..R] (theorem says n)")
for n,R in [(2,12),(3,14),(4,16),(5,18),(6,20)]:
    best=min(G(S) for S in combinations(range(1,R+1),n)); 
    ext=[S for S in combinations(range(1,R+1),n) if G(S)==n and gcd(*S)==1]
    print(n,R,best,"extremal gcd-1 sets:",ext)
print("== T1 (reading i/iii, 'supermultiplicative subsets'): G(A) >= m_p(A)*m_q(A)?  m_k = min G over k-subsets")
for (p,q,R) in [(2,2,12),(2,3,13),(3,3,12)]:
    n=p*q; bad=None; cnt=0; tot=0
    for S in combinations(range(1,R+1),n):
        tot+=1
        g=G(S)
        if g < mk(S,p)*mk(S,q):
            cnt+=1
            if bad is None or g<bad[1]: bad=(S,g,mk(S,p),mk(S,q))
    print(f"p={p} q={q} R={R}: {cnt}/{tot} sets violate; e.g. {bad}")
print("== T1b: weaker: does every n=pq-set with G(A)<=M contain a p-subset with G<=M/q or a q-subset with G<=M/p ?")
for (p,q,R) in [(2,2,12),(2,3,13),(3,3,12)]:
    n=p*q; cnt=0;tot=0;ex=None
    for S in combinations(range(1,R+1),n):
        tot+=1; g=G(S)
        if not (mk(S,p)*q<=g or mk(S,q)*p<=g):
            cnt+=1; ex=ex or (S,g,mk(S,p),mk(S,q))
    print(f"p={p} q={q}: {cnt}/{tot} violate; e.g. {ex}")
print("== T2 (reading ii, products): G(A.B) <= G(A)G(B) always; equality & |A.B|=|A||B| when supports coprime")
random.seed(1); viol=0; eqc=0; trials=20000
for _ in range(trials):
    A=random.sample(range(1,40),random.randint(2,4)); B=random.sample(range(1,40),random.randint(2,4))
    P={a*b for a in A for b in B}
    if G(P)>G(A)*G(B): viol+=1
print("violations of G(A.B)<=G(A)G(B):",viol,"of",trials)
print("  products of extremal sets: ", [(m,k,len({a*b for a in range(1,m+1) for b in range(1,k+1)}),G({a*b for a in range(1,m+1) for b in range(1,k+1)})) for m,k in [(2,2),(2,3),(3,3),(2,5),(3,5)]], "(m,k,|A.B|,G(A.B))")
print("  does {1..n} factor as A.B with |A|=m,|B|=k, all products distinct?")
for m,k in [(2,2),(2,3),(3,3),(2,5),(3,4)]:
    n=m*k; T=set(range(1,n+1)); found=None
    for A in combinations(range(1,n+1),m):
        for B in combinations(range(1,n+1),k):
            if {a*b for a in A for b in B}==T: found=(A,B)
    print("   ",m,k,found)
print("== T3 (reading i, residue projection): classes of p-free part mod p inside {1..pq}; G(C)/|C| vs 1")
def pfree(a,p):
    while a%p==0:a//=p
    return a
for p,q in [(3,2),(3,5),(5,3),(5,7),(7,5)]:
    A=range(1,p*q+1); cl={}
    for a in A: cl.setdefault(pfree(a,p)%p,[]).append(a)
    print(p,q,[(r,len(C),G(C)) for r,C in sorted(cl.items())])
print("== T4 'transitivity': a/(a,b)>=m, b/(b,c)>=k => some quotient in {a,b,c} >= mk ?")
ex=None
for a in range(1,40):
  for b in range(1,40):
    for c in range(1,40):
      m=a//gcd(a,b);k=b//gcd(b,c)
      if m>=2 and k>=2 and G((a,b,c))<m*k and ex is None: ex=(a,b,c,m,k,G((a,b,c)))
print("counterexample:",ex)
print("== T5 why the prime proof breaks: residues of n-free... for n composite, quotients <n not coprime to n")
for n in [4,6,8,9,10]:
    A=list(range(1,n+1)); 
    print(n,"units mod n:",sum(1 for x in range(1,n) if gcd(x,n)==1),"quotients of {1..n} not coprime to n:",sorted({a//gcd(a,b) for a in A for b in A if gcd(a//gcd(a,b),n)>1 and a//gcd(a,b)<n}))
