from fractions import Fraction as F
from math import factorial
c=F(8,3)
def mu(n):
    r=1;p=2
    while p*p<=n:
        if n%p==0:
            n//=p
            if n%p==0: return 0
            r=-r
        p+=1
    return -r if n>1 else r
def Phi(d):
    v=F(1)
    for e in range(1,d+1):
        if d%e==0: v*=F(2**e-1)**mu(d//e)
    assert v.denominator==1; return v.numerator
def small_factors(m,lim=10**6):
    out={};p=2
    while p<lim and m>1:
        while m%p==0: out[p]=out.get(p,0)+1; m//=p
        p+=1
    if m>1: out[m]=1
    return out
def A(n,k):
    num=F(1)
    for t in range(1,n): num*=1-c*F(2)**(t+k)
    den=F(1)
    for l in range(1,n+1):
        if l!=k: den*=1-F(2)**(l-k)
    return -num/den
for n in range(1,23):
    As=[A(n,k) for k in range(1,n+1)]
    S1=sum(As[k-1]*sum(1/(1-c*2**i) for i in range(1,k+1)) for k in range(1,n+1))
    P=F(1)
    for k in range(1,n+1): P*=1-c*2**k
    base=9**n*P*S1
    ql=1
    for d in range(1,n+1): ql*=Phi(d)
    ql1=1
    for d in range(1,n): ql1*=Phi(d)
    print(n,'den(base)=',small_factors(base.denominator),'| x qlcm_n:', (base*ql).denominator,'| x qlcm_{n-1}:',(base*ql1).denominator)
