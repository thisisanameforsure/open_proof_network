# Which n are closed by the elementary prime-pair criteria of the B-S chain (as formalised in plby/lean-proofs Erdos402.lean)?
#  pair (j=0): primes p,q with n<p<2n, (2n-p)^2<=n, p-n<=q<=n         (grahamBound_of_short_prime_pair)
#  shape cert: p prime, n<p<2n, j<=3, 3n<=2p, 3<p-n, (2n-p)^2<=(j+1)n, |collisionShapes| < #primes in [p-n,n]
from math import isqrt
M=200000
sv=bytearray([1])*(2*M+2); sv[0]=sv[1]=0
for i in range(2,isqrt(2*M+1)+1):
    if sv[i]: sv[i*i::i]=bytearray(len(sv[i*i::i]))
pre=[0]*(2*M+3)
for i in range(2*M+2): pre[i+1]=pre[i]+sv[i]
def npr(lo,hi): return pre[hi+1]-pre[max(lo,0)] if hi>=lo else 0
def pair(n):
    for k in range(1,isqrt(n)+1):
        p=2*n-k
        if p>n and sv[p] and npr(p-n,n)>0: return True
    return False
def shape(n):
    for k in range(0,2*isqrt(n)+1):
        p=2*n-1-k
        if not(p>n and sv[p]) or 3*n>2*p or p-n<=3: continue
        for j in range(4):
            if (2*n-p)**2>(j+1)*n: continue
            S=set()
            for ell in range(1,j+1):
                for Y in range(1,isqrt(p)+1):
                    a=p-ell*Y*(Y+1)
                    if (p+1)//2<=a<=n: S.add(a)
            if len(S)<npr(p-n,n): return True
    return False
openn=lambda n: not sv[n] and not sv[n-1]
for hi in [100,1000,7000,50000,200000]:
    rng=[n for n in range(10,hi+1)]
    op=[n for n in rng if openn(n)]
    fp=[n for n in op if not pair(n)]
    line=f"n in 10..{hi}: open (not p, not p+1): {len(op)}; pair criterion fails on {len(fp)} ({100*len(fp)/len(op):.1f}%)"
    if hi<=7000:
        fs=[n for n in rng if not shape(n)]
        line+=f"; shape-certificate failures (all n): {fs[:20]}"
    print(line)
    if hi==100: print("   open n<=100 where pair fails:",fp)
