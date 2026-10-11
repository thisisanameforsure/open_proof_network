# 402-R4-c numeric tests of the clean-room lemma chain
from math import gcd, isqrt
from itertools import combinations
import random
def isp(m): return m>1 and all(m%i for i in range(2,isqrt(m)+1))
# T1 rectangle lemma: p prime, n<p<2n, (2n-p)^2<=n, al+be=p, al,be<n, u!=w
#   => among {al*u, be*u, al*w, be*w} some quotient x/gcd(x,y) >= n
bad=0;cnt=0
for n in range(2,70):
    for p in range(n+1,2*n):
        if not isp(p) or (2*n-p)**2>n: continue
        for al in range(p-n+1,n):
            be=p-al
            for u in range(1,60):
                for w in range(u+1,60):
                    S=[al*u,be*u,al*w,be*w]; cnt+=1
                    if max(x//gcd(x,y) for x in S for y in S)<n: bad+=1
print("T1 rectangle: cases",cnt,"violations",bad)
# T1b: sharpness: same with (2n-p)^2 <= 2n allowed -> violations exist?
bad=[]
for n in range(2,70):
    for p in range(n+1,2*n):
        if not isp(p) or (2*n-p)**2<=n or (2*n-p)**2>4*n: continue
        for al in range(p-n+1,n):
            be=p-al
            for u in range(1,40):
                for w in range(u+1,40):
                    S=[al*u,be*u,al*w,be*w]
                    if max(x//gcd(x,y) for x in S for y in S)<n: bad.append((n,p,al,u,w))
print("T1b beyond the threshold: violations",len(bad),bad[:5])
# T2 collision count: A of size n, all quotients < p (p prime), p does not divide elements
#   => residues mod p distinct, and #unordered pairs with a/g+b/g = p  >= n-(p-1)/2
random.seed(1);viol=0;tested=0
for p in [5,7,11,13]:
    for N in range(2,p):
        U=list(range(1,3*p))
        for _ in range(4000):
            A=random.sample(U,N)
            if any(a%p==0 for a in A): continue
            if max(a//gcd(a,b) for a in A for b in A)>=p: continue
            tested+=1
            if len({a%p for a in A})<N: viol+=1
            pairs=sum(1 for a,b in combinations(A,2) if (a+b)//gcd(a,b)==p)
            if pairs<N-(p-1)//2: viol+=1
print("T2 collision: sets tested",tested,"violations",viol)
# T2b: equal p-adic valuation when all quotients < p
viol=0
for p in [3,5,7]:
    for _ in range(20000):
        A=random.sample(range(1,6*p),3)
        if max(a//gcd(a,b) for a in A for b in A)<p:
            v=lambda a:(0 if a%p else 1+ (0 if (a//p)%p else 1))
            if len({v(a) for a in A})>1: viol+=1
print("T2b valuation: violations",viol)
# T3 criterion C(n): exists prime p, n<p<2n, (2n-p)^2<=n. exceptions among n>=2
M=200000
sv=bytearray([1])*(2*M+2); sv[0]=sv[1]=0
for i in range(2,isqrt(2*M+1)+1):
    if sv[i]: sv[i*i::i]=bytearray(len(sv[i*i::i]))
def crit(n): return any(sv[2*n-k] for k in range(1,isqrt(n)+1) if 2*n-k>n)
exc=[n for n in range(2,M+1) if not crit(n)]
print("T3 n in 2..%d with no prime in [2n-sqrt n,2n):"%M,len(exc),exc)
op=[n for n in exc if not sv[n] and not sv[n-1]]
print("   of which open (n, n-1 not prime):",len(op),op)
# witness table size: least k per n
import collections
print("   max n exception:",max(exc))
