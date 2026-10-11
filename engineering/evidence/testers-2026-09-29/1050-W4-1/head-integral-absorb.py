exec(open('head-integral-by-difference.py').read().split('for n in range(1,19):')[0])
from math import gcd
# For each n and each d < n with Phi_d(2) not a power of 3: is Phi_d(2) "needed" (removing it from L_{n-1} breaks integrality)?
# Hypothesis: d is NOT needed iff Phi_d(2) divides prod_{k=1..n}(3 - 8*2^k) (the numerator factors of 9^n P).
ok=True
for n in range(2,31):
    As={k:A(n,k) for k in range(1,n+1)}
    P=F(1)
    for k in range(1,n+1): P*=1-c*2**k
    H=F(0); S1=F(0)
    for k in range(1,n+1):
        H+=1/(1-c*2**k); S1+=As[k]*H
    base=9**n*P*S1
    L=1
    for d in range(1,n): L*=Phi(d)
    Pn=1
    for k in range(1,n+1): Pn*=abs(3-8*2**k)
    for d in range(1,n):
        ph=Phi(d); r=ph
        while r%3==0: r//=3
        if r==1: continue
        needed=(base*(L//ph)).denominator!=1
        absorbed=all(Pn% p==0 for p in fac(r))
        if needed==absorbed:
            ok=False; print('counterexample n',n,'d',d,'Phi',ph,fac(ph),'needed',needed,'divides prod(3-8*2^k)',absorbed)
print('hypothesis holds for n=2..30:',ok)
