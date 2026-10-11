# 69-R5-a: PROXY for h4e (the hypothesis z >= modulus ~ 10^686 cannot be met by any computation).
# M=2, P=49, real construction, omega cut at a SMALL z: compare the mean over t<T of e(q signedTailBelow_z(t))
# with the full-period (independent primes) value prod_p phi_p.  Mechanism test only.
import math, numpy as np, sys
from model import build, crt, primerange
M,P=2,49; U=3*M+48
H,L=build(M,P); n0,W=crt(L)
us=np.arange(3*M+1,U+1); w=2.0**(-us); sgs=np.array([sg for (_,_,sg) in L],dtype=float)
for z in [100,300,1000]:
    Tmax=3_000_000
    t=np.arange(Tmax,dtype=np.int64); S=np.zeros(Tmax); const=0.0; model={q:1+0j for q in (1,2,5)}
    for p in primerange(P+1,z+1):
        ap=np.array([a%p for (a,_,_) in L],dtype=np.int64); bp=np.array([(n0+sh)%p for (_,sh,_) in L],dtype=np.int64)
        r=(bp[:,None]+ap[:,None]*us[None,:])%p
        C=np.zeros(p); np.add.at(C,r.ravel(),(sgs[:,None]*w[None,:]).ravel())
        # p | n0 + x + W t  <=>  (n0+x) = -W t mod p ; table indexed by (n0+x) mod p
        Wp=W%p
        S+=C[(-Wp*t)%p]
        for q in model: model[q]*= np.exp(2j*np.pi*q*C).mean() if Wp else np.exp(2j*np.pi*q*C[0])
    for q in (1,2,5):
        row=[]
        for T in (10**3,10**4,10**5,10**6,3*10**6):
            emp=np.exp(2j*np.pi*q*S[:T]).mean()
            row.append(f"T={T:.0e} (A={math.log(T)/math.log(z):.2f}): |emp-model|={abs(emp-model[q]):.2e}")
        print(f"z={z} q={q} |model|={abs(model[q]):.4f}  "+"  ".join(row))
