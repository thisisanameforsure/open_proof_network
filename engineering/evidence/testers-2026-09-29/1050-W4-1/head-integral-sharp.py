exec(open('head-integral-by-difference.py').read().split('for n in range(1,19):')[0])
from math import gcd
for n in range(2,31):
    As={k:A(n,k) for k in range(1,n+1)}
    P=F(1)
    for k in range(1,n+1): P*=1-c*2**k
    H=F(0); S1=F(0)
    for k in range(1,n+1):
        H+=1/(1-c*2**k); S1+=As[k]*H
    base=9**n*P*S1
    # minimal odd non-3 multiplier needed: denominator of base, stripped of 3s
    den=base.denominator
    L=1
    for d in range(1,n): L*=Phi(d)
    needed=[d for d in range(1,n) if (base*(L//Phi(d))).denominator!=1]
    print(n,'den(9^n P S1)=',fac(den),'| d<n whose Phi_d(2) is needed:',needed,flush=True)
