# E1: multiset Marica-Schonheim: is #distinct{a/gcd(a,b)} >= |A| for integer sets?
from math import gcd
from itertools import combinations, product
import random
def Q(A): return {a//gcd(a,b) for a in A for b in A}
print("exhaustive subsets of [1..R]")
for n,R in [(2,40),(3,40),(4,30),(5,26),(6,22),(7,20),(8,19)]:
    bad=None;mn=99
    for S in combinations(range(1,R+1),n):
        c=len(Q(S)); 
        if c<mn: mn=c; bad=S
    print(n,R,"min #quotients",mn,bad)
print("exhaustive subsets of exponent grids (2 primes), by vectors")
def Qv(A): return {tuple(max(x-y,0) for x,y in zip(a,b)) for a in A for b in A}
for dims in [(3,3),(4,3),(4,4),(2,2,2),(3,2,2),(5,3)]:
    pts=list(product(*[range(d) for d in dims])); N=len(pts)
    if N>20:
        random.seed(0); worst=None
        for _ in range(300000):
            k=random.randint(2,N); S=random.sample(pts,k); d=len(Qv(S))-k
            if worst is None or d<worst[0]: worst=(d,S)
        print(dims,"random min (#Q-|A|):",worst)
    else:
        worst=None
        for m in range(1,1<<N):
            S=[pts[i] for i in range(N) if m>>i&1]; d=len(Qv(S))-len(S)
            if worst is None or d<worst[0]: worst=(d,S)
        print(dims,"exhaustive min (#Q-|A|):",worst)
