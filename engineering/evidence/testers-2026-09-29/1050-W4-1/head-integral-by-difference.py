from fractions import Fraction as F
import sys
sys.path.insert(0,'.')
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
    return v.numerator
def A(n,k):
    num=F(1)
    for t in range(1,n): num*=1-c*F(2)**(t+k)
    den=F(1)
    for l in range(1,n+1):
        if l!=k: den*=1-F(2)**(l-k)
    return -num/den
def fac(m):
    out={};p=2
    while p<10**5 and m>1:
        while m%p==0: out[p]=out.get(p,0)+1; m//=p
        p+=1
    if m>1: out[m]=1
    return out
for n in range(1,19):
    As={k:A(n,k) for k in range(1,n+1)}
    P=F(1)
    for k in range(1,n+1): P*=1-c*2**k
    L=1
    for d in range(1,n): L*=Phi(d)
    W=9**n*P*L
    S1=sum(As[k]*sum(1/(1-c*2**i) for i in range(1,k+1)) for k in range(1,n+1))
    Us=[sum(As[k]/(1-c*F(2)**(k-j)) for k in range(j+1,n+1)) for j in range(0,n)]
    assert sum(Us)==S1
    bad=[(j,fac((W*u).denominator)) for j,u in enumerate(Us) if (W*u).denominator!=1]
    print(n,'S1 ok' if (W*S1).denominator==1 else 'S1 BAD', 'per-j bad:',bad[:4])
