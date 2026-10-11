# For 2k<=n<k^2: list n where no prime p<=k has n%p < k%p (h3b failures), vs true exceptions (no prime p<=k divides C(n,k)).
import sys
from math import comb
K=int(sys.argv[1])
def primes(m):
    s=[1]*(m+1); s[0]=s[1]=0
    for i in range(2,int(m**.5)+1):
        if s[i]: s[i*i::i]=[0]*len(s[i*i::i])
    return [i for i in range(m+1) if s[i]]
P=primes(K)
lastdigit=[];true=[]
for k in range(2,K+1):
    ps=[p for p in P if p<=k]
    for n in range(2*k,k*k):
        if all(n%p>=k%p for p in ps):
            lastdigit.append((n,k))
            c=comb(n,k)
            if all(c%p for p in ps): true.append((n,k))
print("h3b failures:",lastdigit)
print("true exceptions:",true)
