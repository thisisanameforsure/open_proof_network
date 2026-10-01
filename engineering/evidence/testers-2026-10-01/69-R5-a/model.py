# 69-R5-a: exact-arithmetic construction + double-precision local factors of the independent-primes model.
# phi_p = (1/p) sum_{a mod p} e(q C_p(a)),  C_p(a) = sum over (line d, depth u>3M) with n0+shift_d+dil_d*u = a mod p of sign_d 2^-u.
import itertools, math, cmath, sys
import numpy as np
def primes_upto(n):
    s=np.ones(n+1,bool); s[:2]=False
    for i in range(2,int(n**0.5)+1):
        if s[i]: s[i*i::i]=False
    return [int(x) for x in np.nonzero(s)[0]]
def primerange(a,b): return [p for p in primes_upto(b-1) if p>=a]
def primorial_(P,nth=False):
    r=1
    for p in primes_upto(P): r*=p
    return r
def build(M,P):
    H=int(primorial_(P,nth=False))
    gd=lambda r,k: ([5,1,0,6,4,2] if r%2==0 else [4,2,0,6,5,1])[k]
    sd=lambda r,k: ([3*r+10,15*r+14,18*r+18,6,6*r+8,12*r+16] if r%2==0 else [6*r+12,12*r+12,18*r+18,6,3*r+6,15*r+18])[k]
    L=[]
    for d in itertools.product(range(6),repeat=M):
        g=sum(7**r*gd(r,d[r]) for r in range(M)); s=sum(7**r*sd(r,d[r]) for r in range(M))
        sg=(-1)**sum(d); L.append((1+H*(1+g),H*s,sg))
    return H,L
def crt(L):
    n0,W=0,1
    for (a,sh,_) in L:
        assert math.gcd(a,W)==1
        # n0 + W*k = -sh mod a
        k=((-sh-n0)*pow(W,-1,a))%a; n0+=W*k; W*=a
    for (a,sh,_) in L: assert (n0+sh)%a==0
    return n0,W
def local(M,L,n0,W,p,q,U):
    # returns phi_p and C table
    C=np.zeros(p)
    us=np.arange(3*M+1,U+1); w=2.0**(-us)
    for (a,sh,sg) in L:
        r=((n0+sh)%p + (a%p)*us)%p
        np.add.at(C,r,sg*w)
    return C
if __name__=="__main__":
    M=int(sys.argv[1]); P=int(sys.argv[2]); zmax=int(sys.argv[3]); U=3*M+48
    H,L=build(M,P); n0,W=crt(L)
    print(f"M={M} P={P} lines={len(L)} log10(modulus)={math.log10(W):.1f} depth cut U={U}")
    from collections import defaultdict
    qs=sorted(set([1,2,3,5,8,64,2**(3*M),2**(3*M+1),3*2**(3*M)]))
    A=np.array([a for (a,sh,sg) in L],dtype=object); 
    cx=defaultdict(float)
    for (a,sh,sg) in L:
        for u in range(3*M+1,U+1): cx[sh+a*u]+=sg*2.0**(-u)
    cv=np.array(list(cx.values()))
    kint={q:float(np.sum(1-np.cos(2*np.pi*q*cv))) for q in qs}
    us=np.arange(3*M+1,U+1); w=2.0**(-us)
    S={q:0.0 for q in qs}; worst={q:1e9 for q in qs}; nb={q:0 for q in qs}; rec=0.0; npr=0; nW=0
    sgs=np.array([sg for (_,_,sg) in L],dtype=float)
    for p in primerange(P+1,zmax+1):
        if W%p==0: nW+=1; continue
        ap=np.array([a%p for (a,_,_) in L],dtype=np.int64); bp=np.array([(n0+sh)%p for (_,sh,_) in L],dtype=np.int64)
        r=(bp[:,None]+ap[:,None]*us[None,:])%p
        C=np.zeros(p); np.add.at(C,r.ravel(),(sgs[:,None]*w[None,:]).ravel())
        rec+=1/p; npr+=1
        for q in qs:
            phi=np.exp(2j*np.pi*q*C).mean(); kp=p*(1-abs(phi)); S[q]+=-math.log(abs(phi)); worst[q]=min(worst[q],kp); nb[q]+= kp<kint[q]/2
    print(f"primes in ({P},{zmax}] not dividing W: {npr} (dividing W: {nW}); sum 1/p={rec:.4f}")
    for q in qs:
        print(f"q={q:7d} kappa_int={kint[q]:.3e} -log|prod phi_p|={S[q]:.4e} kappa_eff={S[q]/rec:.3e} min_p p(1-|phi_p|)={worst[q]:.3e} primes with kappa_p<kappa_int/2: {nb[q]}  kappa_eff*100^M={S[q]/rec*100**M:.3g} kappa_eff*64^M={S[q]/rec*64**M:.3g}")
