# Checks, in exact rationals, each step of a paper proof of C(n): 3^(n-1) * L_{n-1} * sum_k k*A(n,k) is an integer.
from fractions import Fraction as F
exec(open('head-integral-by-difference.py').read().split('def A(n,k):')[0])
def A(n,k):
    num=F(1)
    for t in range(1,n): num*=1-c*F(2)**(t+k)
    den=F(1)
    for l in range(1,n+1):
        if l!=k: den*=1-F(2)**(l-k)
    return -num/den
def qf(m):  # [m]! = prod_{j<=m} (2^j - 1)
    r=1
    for j in range(1,m+1): r*=2**j-1
    return r
def G(m,k): return qf(m)//(qf(k)*qf(m-k))
def Nx(n,x):  # N(x) = prod_{t=1}^{n-1} (3 - 8*2^t*x), integer polynomial in x of degree n-1
    r=1
    for t in range(1,n): r*=3-8*2**t*x
    return r
def Ncoeffs(n):
    p=[1]
    for t in range(1,n):
        a=-8*2**t; q=[0]*(len(p)+1)
        for i,v in enumerate(p): q[i]+=3*v; q[i+1]+=a*v
        p=q
    return p
ok1=ok2=ok3=ok4=True
for n in range(1,26):
    m=n-1
    L=1
    for d in range(1,n): L*=Phi(d)
    # step 1: D_k = (-1)^(n-k) 2^(-C(k,2)) [k-1]! [n-k]!
    for k in range(1,n+1):
        D=F(1)
        for l in range(1,n+1):
            if l!=k: D*=1-F(2)**(l-k)
        ok1&= D==F((-1)**(n-k)*qf(k-1)*qf(n-k),2**(k*(k-1)//2))
    # step 2: 3^(n-1) A(n,k) = -(-1)^(n-k) 2^C(k,2) G(m,k-1) N(2^k) / [m]!
    for k in range(1,n+1):
        ok2&= 3**(n-1)*A(n,k)==F(-(-1)**(n-k)*2**(k*(k-1)//2)*G(m,k-1)*Nx(n,2**k),qf(m))
    # step 3: q-binomial theorem sum_{k'} (-1)^k' 2^C(k',2) G(m,k') z^k' = prod_{i<m} (1 - z 2^i), and its z-derivative form
    a=Ncoeffs(n)
    T=sum(k*A(n,k) for k in range(1,n+1))
    tot=F(0)
    for j,aj in enumerate(a):
        z=2**(j+1)
        Pz=1
        for i in range(m): Pz*=1-z*2**i
        dPz=0
        for i in range(m):
            t=-z*2**i
            for i2 in range(m):
                if i2!=i: t*=1-z*2**i2
            dPz+=t
        lhs0=sum((-1)**kp*2**(kp*(kp-1)//2)*G(m,kp)*z**kp for kp in range(m+1))
        lhs1=sum(kp*(-1)**kp*2**(kp*(kp-1)//2)*G(m,kp)*z**kp for kp in range(m+1))
        ok3&= lhs0==Pz and lhs1==dPz
        # step 4: each piece, divided by [m]!, is cleared by L_m = L_{n-1}
        ok4&= (F(Pz,qf(m))).denominator==1
        for i in range(m):
            t=z*2**i
            for i2 in range(m):
                if i2!=i: t*=1-z*2**i2
            ok4&= (F(t,qf(m))*L).denominator==1
        tot+=aj*2**j*(Pz+dPz)
    # step 5: reassembly: 3^(n-1) T = -(-1)^(n-1) * tot / [m]!
    ok5 = 3**(n-1)*T==F(-(-1)**(n-1)*tot,qf(m))
    if not ok5: print('reassembly fails at n',n)
print('D_k formula',ok1,'| 3^(n-1)A formula',ok2,'| q-binomial and derivative',ok3,'| pieces cleared by L_{n-1}',ok4)
