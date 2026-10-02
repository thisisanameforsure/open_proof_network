# Part B: exact charMean of 69-R2-b's definitions for M = 1, P = 7 (H = 210), T up to 4000, q = 1..16.
# omega is exact: sieve by primes < B = 2e6, cofactor < B^3 so it is 1, a prime, a prime square or a product of two primes.
import numpy as np, math, cmath, sys, random
M=1; H=210; U=40; T=int(sys.argv[1]) if len(sys.argv)>1 else 4000; B=2_000_000
gd=[5,1,0,6,4,2]; sd=[10,14,18,6,8,16]
dil=[1+H*(1+g) for g in gd]; shift=[H*s for s in sd]; sign=[(-1)**k for k in range(6)]
mod=math.prod(dil)
# CRT base point
n0=0; m=1
for a,s in zip(dil,shift):
    while (n0+s)%a: n0+=m
    m*=a
assert n0<mod and all((n0+s)%a==0 for a,s in zip(dil,shift))
start=[(n0+s)//a for a,s in zip(dil,shift)]; step=[mod//a for a in dil]
sv=np.ones(B+1,bool); sv[:2]=False
for i in range(2,int(B**.5)+1):
    if sv[i]: sv[i*i::i]=False
primes=np.nonzero(sv)[0]
def is_prime(n):
    if n<2: return False
    d=n-1; r=0
    while d%2==0: d//=2; r+=1
    for b in (2,3,5):
        x=pow(b,d,n)
        if x in (1,n-1): continue
        for _ in range(r-1):
            x=x*x%n
            if x==n-1: break
        else: return False
    return True
def facs(n):
    f=set(); p=2
    while p*p<=n:
        while n%p==0: f.add(p); n//=p
        p+=1
    if n>1: f.add(n)
    return f
tails=np.zeros((6,T))
for li in range(6):
    assert step[li]*T+start[li]+U < 2**63
    V=(start[li]+step[li]*np.arange(T,dtype=object)[:,None]+np.arange(1,U+1,dtype=object)[None,:]).astype(np.int64)
    rem=V.copy(); cnt=np.zeros((T,U),np.int64)
    for p in primes:
        p=int(p)
        inv=pow(step[li]%p,-1,p) if step[li]%p else None
        if inv is None:
            # p divides step: v = start+u mod p, independent of t
            for u in range(1,U+1):
                if (start[li]+u)%p==0:
                    cnt[:,u-1]+=1
                    while (rem[:,u-1]%p==0).all(): rem[:,u-1]//=p
                    mk=rem[:,u-1]%p==0
                    while mk.any(): rem[mk,u-1]//=p; mk=rem[:,u-1]%p==0
            continue
        base=(-(start[li])*inv)%p
        for u in range(1,U+1):
            t0=(base-u*inv)%p
            if t0>=T: continue
            col=rem[t0::p,u-1]; cnt[t0::p,u-1]+=1
            col//=p
            mk=col%p==0
            while mk.any():
                col[mk]//=p; mk=col%p==0
    # cofactors
    extra=np.zeros((T,U),np.int64)
    it=np.nonzero(rem>1)
    for t,u in zip(*it):
        c=int(rem[t,u])
        if is_prime(c): extra[t,u]=1
        else:
            r=math.isqrt(c); extra[t,u]=1 if r*r==c else 2
    om=cnt+extra
    fa=facs(dil[li])
    for p in fa:   # omega(a*v) = omega(v) + #{p | a, p not| v}
        om+= (V%p!=0)
    w=0.5**np.arange(1,U+1)
    tails[li]=om@w
    print("line",li,"dil",dil[li],"mean omega",om.mean(),flush=True)
S=sum(sign[i]*tails[i] for i in range(6))
np.save("signedTail_M1_P7.npy",S)
print("T",T,"signedTail mean",S.mean(),"std",S.std())
for TT in [T//8,T//4,T//2,T]:
    print("T=",TT," |charMean| q=1..16:",[round(abs(np.exp(2j*np.pi*q*S[:TT]).mean()),3) for q in range(1,17)])
print("noise floor 1/sqrt(T) =",T**-.5)
