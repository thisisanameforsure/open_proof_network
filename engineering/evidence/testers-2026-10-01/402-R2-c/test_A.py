# exhaustive test of Theorem A: B subset [1..R], N any, all pairs a < N*gcd(a,b); p prime;
# M = lcm(1..floor((N-1)/p)); claim u*v < N*M.  Also record tightness.
import itertools, math, sys
from math import gcd
def lcm_upto(k):
    r=1
    for i in range(1,k+1): r=r*i//gcd(r,i)
    return r
R=int(sys.argv[1]); primes=[2,3,5,7,11,13]
worst={}
cnt=0
def rec(B,start,Nmin):
    # Nmin = minimal N making B strict = max over pairs floor(a/g)+1
    global cnt
    if B:
        for N in range(Nmin, Nmin+3):
            for p in primes:
                if p>R: break
                u=sum(1 for a in B if a%p==0); v=len(B)-u
                M=lcm_upto((N-1)//p)
                cnt+=1
                assert u*v < N*M, (B,N,p)
                if u and v:
                    key=(N,p); r=u*v/(N*M)
                    if r>worst.get(key,(0,))[0]: worst[key]=(r,list(B),u,v,M)
    for x in range(start,R+1):
        nm=Nmin
        for a in B:
            g=gcd(a,x); nm=max(nm,a//g+1,x//g+1)
        if nm>MAXN: continue
        B.append(x); rec(B,x+1,max(nm,2)); B.pop()
MAXN=int(sys.argv[2])
rec([],1,1)
print("checked",cnt,"ok")
for k in sorted(worst): 
    if worst[k][0]>0.3: print(k,worst[k])
