# 402-R5-a: test the criterion's STATEMENT: for n with a window prime, is there a set of n positive
# integers <= M with every quotient a/gcd(a,b) < n ?  Exhaustive clique search (backtracking) on [1..M].
import sys, math, time
from math import gcd
def window(n):
    return [p for p in range(n+1,2*n) if all(p%d for d in range(2,int(p**.5)+1)) and (2*n-p)**2<=n]
def maxstrict(n,M,limit):
    # largest set in [1..M] with all quotients < n (strict). returns size found (stops at n) and node count
    adj={a:[b for b in range(a+1,M+1) if a<n*gcd(a,b) and b<n*gcd(a,b)] for a in range(1,M+1)}
    best=0; nodes=0; t0=time.time()
    def rec(size,cand):
        nonlocal best,nodes
        nodes+=1
        if size>best: best=size
        if best>=n or time.time()-t0>limit: return
        if size+len(cand)<=best: return   # cannot beat best
        if size+len(cand)<n: return
        for i,a in enumerate(cand):
            if size+len(cand)-i<n: break
            s=set(adj[a]); rec(size+1,[b for b in cand[i+1:] if b in s])
            if best>=n: return
    rec(0,list(range(1,M+1)))
    return best,nodes,time.time()-t0
for n,M in [(2,400),(3,400),(4,300),(6,200),(7,150),(9,120),(10,100),(11,90),(12,80),(13,70),(15,60),(16,60),(5,300),(8,150),(14,60)]:
    w=window(n); b,nodes,t=maxstrict(n,M,120)
    print(f"n={n} window primes={w} M={M}: largest strict set found {b} (need {n} to refute) nodes={nodes} t={t:.1f}s {'TIMEOUT' if t>120 else 'exhaustive'}",flush=True)
