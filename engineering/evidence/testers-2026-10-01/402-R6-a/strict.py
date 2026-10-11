# 402-R6-a, independent. Search for a counterexample to r5b_gen_criterion's CONCLUSION at sizes where the simple
# window fails but the generalised hypotheses hold (5, 8, 14, 18): a set A of n integers in [1..M], no element divisible by a
# prime q with 3q >= n, and no pair with gcd(a,b)*n <= a (pairs include a=b only for n=1). Max clique by bitset B&B.
import sys, time
from math import gcd
def run(n,M,budget):
    def smooth(a):
        d=2
        while d*d<=a:
            while a%d==0:
                if 3*d>=n: return False
                a//=d
            d+=1
        return not(a>1 and 3*a>=n)
    V=[a for a in range(1,M+1) if smooth(a)]
    idx={a:i for i,a in enumerate(V)}
    adj=[0]*len(V)
    for i,a in enumerate(V):
        for j in range(i+1,len(V)):
            b=V[j]; g=gcd(a,b)
            if g*n>a and g*n>b: adj[i]|=1<<j; adj[j]|=1<<i
    best=[0]; t0=time.time(); out=[False]
    def rec(size,cand):
        if size>best[0]: best[0]=size
        if size>=n: return True
        if time.time()-t0>budget: out[0]=True; return False
        while cand:
            if size+bin(cand).count("1")<=best[0] and best[0]<n and size+bin(cand).count("1")<n: return False
            v=cand.bit_length()-1; cand&=~(1<<v)
            if rec(size+1,cand&adj[v]): return True
        return False
    found=rec(0,(1<<len(V))-1)
    print(f"n={n} M={M} candidates={len(V)} strict set of size n found={found} largest seen={best[0]} timed_out={out[0]}",flush=True)
for n,M in [(5,3000),(8,3000),(14,3000),(18,3000),(9,3000),(10,3000)]:
    run(n,M,90)
